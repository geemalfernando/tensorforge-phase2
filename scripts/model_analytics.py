"""Recompute measured validation analytics and export figures and Markdown."""
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve, precision_score, recall_score

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.model import TicketModel,compose_text
from scripts.train_model import read_examples

TARGET_NAMES={'category':'Primary category','secondary_category':'Secondary category','is_urgent':'Urgency'}


def build_analytics():
    subprocess.run([sys.executable,str(ROOT/'scripts/evaluate_model.py')],cwd=ROOT,check=True)
    analytics=json.loads((ROOT/'artifacts/evaluation_breakdown.json').read_text())
    config=json.loads((ROOT/'configs/training.json').read_text())
    output=ROOT/'docs/analytics';output.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'figure.dpi':120,'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.titlepad':14,'axes.labelcolor':'#334155','text.color':'#0f172a','axes.edgecolor':'#cbd5e1'})
    figures={}
    def save(name,fig):
        fig.tight_layout();fig.savefig(output/(name+'.png'),bbox_inches='tight',facecolor='white');fig.savefig(output/(name+'.svg'),bbox_inches='tight',facecolor='white');plt.close(fig);figures[name]=str(output/(name+'.png'))
    metrics=['precision','recall','f1-score'];colors=['#0d9488','#65a30d','#6366f1']
    fig,ax=plt.subplots(figsize=(9,4.5));positions=np.arange(3)
    for index,metric in enumerate(metrics):
        values=[analytics['classification_reports'][target]['macro avg'][metric] for target in TARGET_NAMES]
        bars=ax.bar(positions+(index-1)*.24,values,.22,label=metric.replace('-score','').title(),color=colors[index])
        ax.bar_label(bars,labels=[f'{value:.1%}' for value in values],padding=3,fontsize=9)
    ax.set_xticks(positions,list(TARGET_NAMES.values()));ax.set_ylim(0,1.12);ax.set_ylabel('Macro-average score');ax.set_title('Fresh Desk · Precision, recall and F1 across all three outputs');ax.legend(loc='upper left',ncols=3,frameon=False);save('model-summary',fig)
    fig,ax=plt.subplots(figsize=(11,6));report=analytics['classification_reports']['category'];labels=[label for label,value in report.items() if isinstance(value,dict) and label not in ('macro avg','weighted avg','micro avg')];positions=np.arange(len(labels))
    for index,metric in enumerate(metrics):ax.barh(positions+(index-1)*.23,[report[label][metric] for label in labels],.21,color=colors[index],label=metric.replace('-score','').title())
    ax.set_yticks(positions,[name.replace('_',' ') for name in labels]);ax.invert_yaxis();ax.set_xlim(0,1.05);ax.set_xlabel('Validation score');ax.set_title('Primary category · Per-class precision, recall and F1');ax.legend(frameon=False,ncols=3,loc='lower right');save('primary-class-scores',fig)
    for target,details in analytics['confusion_matrices'].items():
        matrix=np.array(details['rows_actual_columns_predicted']);labels=details['labels'];size=9 if len(labels)>6 else 7
        fig,ax=plt.subplots(figsize=(size,size*.82));im=ax.imshow(matrix,cmap='YlGnBu');fig.colorbar(im,ax=ax,label='Ticket count',shrink=.8)
        ax.set_xticks(np.arange(len(labels)),[label.replace('_',' ') for label in labels],rotation=60,ha='right');ax.set_yticks(np.arange(len(labels)),[label.replace('_',' ') for label in labels]);ax.set_xlabel('Predicted label');ax.set_ylabel('True label');ax.set_title(TARGET_NAMES[target]+' · Validation confusion matrix')
        for i in range(len(labels)):
            for j in range(len(labels)):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',fontsize=8 if len(labels)>6 else 11,color='white' if matrix[i,j]>.5*matrix.max() else '#1e293b')
        save(target+'-confusion',fig)
    languages=analytics['category_by_language'];fig,ax=plt.subplots(figsize=(9,4.5));bars=ax.bar(list(languages),[v['accuracy'] for v in languages.values()],color='#0d9488');ax.bar_label(bars,labels=[f"{v['accuracy']:.1%}\nn={v['count']}" for v in languages.values()],padding=4);ax.set_ylim(0,1.08);ax.set_ylabel('Primary accuracy');ax.set_title('Primary accuracy by language · Small groups have high uncertainty');save('language-accuracy',fig)
    tickets,_,_,urgent=read_examples(ROOT/'datasets/validation.csv');model=TicketModel.load();labels=list(model.urgent_model.named_steps['classifier'].classes_);probabilities=model.urgent_model.predict_proba([compose_text(t) for t in tickets])[:,labels.index('true')];truth=np.array([value=='true' for value in urgent]);precision,recall,thresholds=precision_recall_curve(truth,probabilities);raw=probabilities>=model.urgent_threshold
    fig,ax=plt.subplots(figsize=(8,4.5));ax.plot(recall,precision,color='#0d9488',linewidth=2,label='Urgency classifier');ax.scatter([recall_score(truth,raw)],[precision_score(truth,raw)],color='#f97316',s=65,label=f'Configured cutoff {model.urgent_threshold:.0%}');ax.set(xlim=(0,1.03),ylim=(0,1.03),xlabel='Recall',ylabel='Precision',title='Urgency · Precision–recall tradeoff before spam consistency rules');ax.legend(frameon=False);save('urgency-precision-recall',fig)
    analytics['figures']=figures
    summary=['# Fresh Desk — Model analytics','',f"Active artifact: `{analytics['model_version']}`. Evaluated on **{analytics['examples']}** supplied validation tickets; all predictions pass the organizer JSON Schema.",'','These are **development scores**. This validation split informed model configuration and thresholds. It is not an independent test set or evidence of real-world accuracy. Data are synthetic; native-script quality has not been independently reviewed.','', '## Overall results','', '| Model output | Accuracy | Macro precision | Macro recall | Macro F1 | Weighted precision | Weighted recall | Weighted F1 |','| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for target,name in TARGET_NAMES.items():
        report=analytics['classification_reports'][target];macro=report['macro avg'];weighted=report['weighted avg'];values=[report['accuracy'],*[macro[m] for m in metrics],*[weighted[m] for m in metrics]];summary.append('| '+name+' | '+' | '.join(f'{v:.2%}' for v in values)+' |')
    summary+=['','![All three models: macro precision, recall and F1](analytics/model-summary.png)','','## Training and inference details','', '| Output | Estimator | C | Class weights | Character n-grams | Decision cutoff |','| --- | --- | ---: | --- | --- | --- |']
    for target,name in TARGET_NAMES.items():
        values=config['models'][target];summary.append(f"| {name} | {values['estimator']} | {values['C']} | {values['class_weight'] or 'None'} | {values['char_analyzer']} {values['char_ngram_range']} | {values.get('threshold','Highest primary probability')} |")
    summary+=['','Word TF-IDF uses 1–2 grams. Training uses channel, subject and text; excludes ticket IDs and language labels. Secondary uses a three-fold sigmoid-calibrated linear SVM; primary and urgency use logistic regression. Primary probabilities have not been independently calibrated. Narrow category precedence and spam consistency rules are applied after model scoring.','', '## Per-class scores for every trained output','']
    for target,name in TARGET_NAMES.items():
        summary+=['### '+name,'','| Label | Precision | Recall | F1 | Support |','| --- | ---: | ---: | ---: | ---: |']
        for label,values in analytics['classification_reports'][target].items():
            if isinstance(values,dict):summary.append('| '+label+' | '+' | '.join(f"{values[m]:.2%}" for m in metrics)+f" | {int(values['support'])} |")
        summary+=['',f'![{name} confusion matrix](analytics/{target}-confusion.png)','']
    summary+=['![Primary per-class precision, recall and F1](analytics/primary-class-scores.png)','','## Language breakdown','', '| Language | Tickets | Primary accuracy | Macro F1 |','| --- | ---: | ---: | ---: |']
    for language,values in languages.items():summary.append(f"| {language} | {values['count']} | {values['accuracy']:.2%} | {values['macro_f1']:.2%} |")
    summary+=['','![Primary accuracy by language](analytics/language-accuracy.png)','','## Urgency threshold','', 'The configured urgency cutoff is 30%. The following curve shows the classifier probability tradeoff before the API forces spam to nonurgent. Classification tables above score the final API outputs.','', '![Urgency precision–recall curve](analytics/urgency-precision-recall.png)','','## Review and acceptance','',f"{analytics['human_review_count']} of {analytics['examples']} validation predictions recommend human review. The dashboard also sends urgent tickets to the support queue. A message with three or fewer words or primary confidence below 50% requires review. Only an authenticated support role can accept a ticket or override its team, with an explanation required for an override. Raw predictions remain unchanged; the accepted team and support audit entry are stored separately.",'','## Reproduce','', '```bash','python scripts/model_analytics.py','python scripts/build_model_analytics.py --execute','```','','See [the executed Jupyter notebook](../notebooks/model_analytics.ipynb), [frozen training settings](../configs/training.json), and [saved experiments](../artifacts/training_experiments.json). PNG and SVG figures are exported in `docs/analytics/`.']
    (ROOT/'docs/model-analytics.md').write_text('\n'.join(summary)+'\n')
    return analytics


if __name__=='__main__':
    result=build_analytics();print('Created docs/model-analytics.md and '+str(len(result['figures']))+' figure pairs.')
