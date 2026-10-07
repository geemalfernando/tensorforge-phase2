"""Reproduce the development comparisons saved in artifacts/training_experiments.json."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.model import make_classifier,compose_text
from scripts.train_model import read_examples,evaluate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',choices=['category','is_urgent'],default='category')
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/reproduced_comparisons.json')
    args=parser.parse_args()
    train,category,secondary,urgent=read_examples(ROOT/'datasets/train.csv')
    validation,val_category,val_secondary,val_urgent=read_examples(ROOT/'datasets/validation.csv')
    texts=[compose_text(t) for t in train]; val_texts=[compose_text(t) for t in validation]
    if args.target=='category':
        options=[{'estimator':'logistic_regression','C':c,'class_weight':'balanced','normalize':normalize,'char_analyzer':analyzer,'char_ngram_range':[2,6]}
                 for normalize,analyzer,c in [(True,'char_wb',40),(True,'char_wb',8),(True,'char_wb',100),(False,'char_wb',100),(True,'char',40),(False,'char',40)]]
        labels,val_labels=category,val_category
    else:
        options=[{'estimator':'logistic_regression','C':c,'class_weight':weight,'normalize':normalize,'char_analyzer':'char','char_ngram_range':[2,5]}
                 for normalize,c,weight in [(False,3,None),(True,3,None),(True,8,None),(True,40,'balanced')]]
        labels,val_labels=urgent,val_urgent
    results=[]
    for config in options:
        model=make_classifier(**config).fit(texts,np.asarray(labels))
        if args.target=='category':
            result={**config,**evaluate(val_labels,model.predict(val_texts))}
            results.append(result);print(json.dumps(result),flush=True)
        else:
            index=list(model.named_steps['classifier'].classes_).index('true')
            probabilities=model.predict_proba(val_texts)[:,index]
            for threshold in [.1,.2,.3,.4,.5]:
                result={**config,'threshold':threshold,**evaluate(val_labels,['true' if p>=threshold else 'false' for p in probabilities])}
                results.append(result);print(json.dumps(result),flush=True)
    args.output.write_text(json.dumps({'note':'Development validation comparisons, not independent test scores.','target':args.target,'results':results},indent=2)+'\n')


if __name__=='__main__':
    main()
