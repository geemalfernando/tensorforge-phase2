import {useEffect,useMemo,useRef,useState} from 'react';
import {Words,prefersReducedMotion} from './FreshSurface';

// Illustrative examples only; real predictions come from the trained models on the intake page.
const DEMOS=[
 {lang:'English · chat',text:"My order hasn't arrived and it's been an hour.",issue:['Delivery delay',.86],second:['Payment refund',.31],urgency:.28,team:'Delivery Operations'},
 {lang:'Singlish · chat',text:'mage order eka late, refund ekak denna',issue:['Delivery delay',.74],second:['Payment refund',.52],urgency:.18,team:'Delivery Operations'},
 {lang:'தமிழ் · email',text:'என் ஆர்டர்ல ஒரு ஐட்டம் வரல, பணம் திருப்பி தாங்க',issue:['Order missing / wrong',.81],second:['Payment refund',.44],urgency:.12,team:'Food Operations'},
 {lang:'English · call',text:'The driver is not stopping the car and I am scared.',issue:['Safety & conduct',.93],second:['Ride / trip issue',.36],urgency:.94,team:'Trust & Safety',review:true},
 {lang:'English · chat',text:'I left my bag in the car after my ride. Please help.',issue:['Lost item',.89],second:['Ride / trip issue',.22],urgency:.09,team:'Lost & Found'},
];
const TEAMS=['Payments & Refunds','Ride Operations','Lost & Found','Food Operations','Delivery Operations','Restaurant Quality','Account Services','Trust & Safety','Tech Support','Front-line Support','Spam Filter'];
const WORDS=['understanding.','clarity.','care.'];
const STEPS=[['01','Send it in','Chat, email, or call transcript. Start with one ticket or bring a JSON batch.','↗'],['02','See the signals','Inspect issue candidates, urgency probability, and the reason a ticket needs review.','⌁'],['03','Keep people involved','The support role reviews uncertain or urgent tickets and accepts the final team.','◇']];

const graphemes=text=>typeof Intl!=='undefined'&&Intl.Segmenter?[...new Intl.Segmenter(undefined,{granularity:'grapheme'}).segment(text)].map(s=>s.segment):Array.from(text);
function useDemo(reduced) {
 const [state,setState]=useState({index:0,typed:0,phase:'typing'});
 const chars=useMemo(()=>DEMOS.map(d=>graphemes(d.text)),[]);
 useEffect(()=>{
  const total=chars[state.index].length;let next,delay;
  if(state.phase==='typing'){
   if(reduced||state.typed>=total){next={...state,typed:total,phase:reduced?'result':'thinking'};delay=reduced?0:380;}
   else{next={...state,typed:state.typed+1};delay=24+Math.random()*46;}
  } else if(state.phase==='thinking'){next={...state,phase:'result'};delay=950;}
  else{next={index:(state.index+1)%DEMOS.length,typed:0,phase:'typing'};delay=reduced?6500:3800;}
  const timer=setTimeout(()=>setState(next),delay);
  return()=>clearTimeout(timer);
 },[state,chars,reduced]);
 return {...state,demo:DEMOS[state.index],shown:chars[state.index].slice(0,state.typed).join('')};
}

export default function Landing({onStart,onModels,onSupport}) {
 const surface=useRef(null);
 const [reduced]=useState(prefersReducedMotion);
 const [word,setWord]=useState(0);
 const {demo,shown,phase,index}=useDemo(reduced);

 useEffect(()=>{
  if(reduced)return;
  const timer=setInterval(()=>setWord(w=>(w+1)%WORDS.length),2600);
  return()=>clearInterval(timer);
 },[reduced]);

 // Scroll reveal and count-up, observed once per element.
 useEffect(()=>{
  const root=surface.current,targets=root.querySelectorAll('[data-reveal],[data-count]');
  const show=element=>{
   element.classList.add('is-in');
   const goal=Number(element.dataset.count);
   if(!goal||reduced)return;
   const begin=performance.now();
   const tick=now=>{const p=Math.min((now-begin)/1400,1),eased=1-Math.pow(1-p,3);element.textContent=Math.round(goal*eased).toLocaleString();if(p<1)requestAnimationFrame(tick);};
   requestAnimationFrame(tick);
  };
  if(!('IntersectionObserver' in window)){targets.forEach(show);return;}
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){show(entry.target);observer.unobserve(entry.target);}}),{threshold:.2,rootMargin:'0px 0px -40px 0px'});
  targets.forEach(t=>observer.observe(t));
  return()=>observer.disconnect();
 },[reduced]);

 const done=phase==='result';
 return <div className="fresh-landing" ref={surface}>
  <div className="fresh-blob blob-a" aria-hidden="true"/><div className="fresh-blob blob-b" aria-hidden="true"/>

  <section className="fresh-hero">
   <div className="fresh-copy">
    <div className="fresh-eyebrow"><span/>A FRESH START FOR EVERY TICKET</div>
    <h1 aria-label={`Less waiting. More ${WORDS[0]}`}>
     <span aria-hidden="true"><Words text="Less waiting."/><br/><Words text="More" start={2}/>
      <span className="fresh-rotator"><span key={word}>{WORDS[word]}</span></span>
     </span>
    </h1>
    <p>A clearer desk for every customer message. Fresh Desk suggests the issue, urgency, and support team—with people in the loop when a ticket needs care.</p>
    <div className="fresh-actions">
     <button className="fresh-start" data-magnetic data-cursor="Open" onClick={onStart}>Open your desk <span>↗</span></button>
     <button className="fresh-secondary" data-magnetic onClick={onModels}>Meet the models <span>→</span></button>
    </div>
    <div className="fresh-trust"><span><i/>Locally trained models</span><span>සිංහල · தமிழ் · English</span></div>
   </div>

   <div className="fresh-demo" aria-label="Animated example of a ticket being classified and routed">
    <div className="fresh-layer" style={{'--d':-14}} aria-hidden="true"><div className="fresh-orbit"/><div className="fresh-orbit orbit-two"/></div>
    <div className="fresh-layer fresh-card-layer" style={{'--d':10}}>
     <div className="fresh-model-card">
      <div className="fresh-card-top"><span className="fresh-symbol">f<span>✳</span></span><span>FRESH DESK / EXAMPLE FLOW</span><i className={phase==='thinking'?'is-busy':''}/></div>
      <div className="fresh-ticket">
       <small>{demo.lang}</small>
       <p>{shown}<span className={`fresh-caret${phase==='typing'?'':' is-idle'}`}/></p>
      </div>
      <div className={`fresh-scan${phase==='thinking'?' is-on':''}`} aria-hidden="true"><span/></div>
      <div className={`fresh-readout${done?' is-done':''}`} key={index}>
       {[['Main issue',...demo.issue],['Second concern',...demo.second],['Urgency',demo.urgency>.5?'High':'Normal',demo.urgency]].map(([name,value,score],i)=>
        <div className="fresh-meter" key={name} style={{'--i':i,'--v':done?score:0}}>
         <span>{name}<b>{done?value:'—'}</b></span><em><i/></em>
        </div>)}
      </div>
      <div className="fresh-route"><span>Suggested team</span><strong>{done?demo.team:'Thinking…'} <i>↗</i></strong></div>
      <div className="fresh-dots" aria-hidden="true">{DEMOS.map((_,i)=><span key={i} className={i===index?'is-on':''}/>)}</div>
     </div>
    </div>
    <div className="fresh-layer" style={{'--d':26}}>
     <div className="fresh-float float-message"><span className="fresh-tile">✉</span><div><small>A customer message</small><strong>Any language, any channel.</strong></div><span className="fresh-dot"/></div>
    </div>
    <div className="fresh-layer" style={{'--d':34}}>
     <div className={`fresh-float float-review${done&&demo.review?' is-alert':''}`}><span className="fresh-tile review-tile">{done&&demo.review?'!':'✓'}</span><div><small>{done&&demo.review?'Urgent ticket flagged':'When confidence is low'}</small><strong>A person takes a closer look.</strong></div></div>
    </div>
    <div className="fresh-layer" style={{'--d':-30}} aria-hidden="true"><span className="fresh-spark spark-a">✳</span></div>
    <div className="fresh-layer" style={{'--d':40}} aria-hidden="true"><span className="fresh-spark spark-b">✦</span></div>
   </div>
  </section>

  <section className="fresh-facts" aria-label="Fresh Desk capabilities">
   {[['3','trained models'],['11','support routes'],['5000','tickets per batch job']].map(([n,text],i)=><div key={text} data-reveal style={{'--delay':`${i*90}ms`}}><strong data-count={n}>{Number(n).toLocaleString()}</strong><span>{text}</span></div>)}
   <div data-reveal style={{'--delay':'270ms'}}><strong>Human</strong><span>review and acceptance</span></div>
  </section>

  <div className="fresh-marquee" aria-label="Support teams Fresh Desk routes to">
   <div className="fresh-track">{[0,1].map(copy=><ul key={copy} aria-hidden={copy===1}>{TEAMS.map(team=><li key={team}>{team}<span>✳</span></li>)}</ul>)}</div>
  </div>

  <section className="fresh-process">
   <div className="fresh-section-heading" data-reveal><p className="kicker">A little clarity goes a long way</p><h2>A good handoff starts here.</h2><p>One workspace for messages, model signals, and support decisions.</p></div>
   <div className="fresh-feature-grid">
    <div className="fresh-line" data-reveal aria-hidden="true"/>
    {STEPS.map(([n,title,text,icon],i)=><article key={n} data-spot data-reveal style={{'--delay':`${i*120}ms`}}><div><span>{n}</span><b>{icon}</b></div><h3>{title}</h3><p>{text}</p></article>)}
   </div>
  </section>

  <section className="fresh-support-cta" data-spot data-reveal>
   <div><p className="kicker">For your support team</p><h2>A shared queue.<br/>A thoughtful decision.</h2><p>Review the message and model details, confirm a route, and save acceptance for the customer to see.</p></div>
   <button data-magnetic data-cursor="Enter" onClick={onSupport}>Enter support workspace <span>↗</span></button>
  </section>
 </div>;
}
