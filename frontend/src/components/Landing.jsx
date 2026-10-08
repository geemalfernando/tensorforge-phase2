import {useEffect,useRef} from 'react';

export default function Landing({onStart,onModels,onSupport}) {
 const surface=useRef(null),frame=useRef(null);
 useEffect(()=>()=>cancelAnimationFrame(frame.current),[]);
 function move(event) {
  if(matchMedia('(prefers-reduced-motion: reduce)').matches||event.pointerType==='touch')return;
  const element=surface.current,box=element.getBoundingClientRect(),x=event.clientX-box.left,y=event.clientY-box.top;
  cancelAnimationFrame(frame.current);
  frame.current=requestAnimationFrame(()=>{element.style.setProperty('--cursor-x',`${x}px`);element.style.setProperty('--cursor-y',`${y}px`);element.style.setProperty('--tilt-x',`${(y/box.height-.5)*-5}deg`);element.style.setProperty('--tilt-y',`${(x/box.width-.5)*7}deg`);});
 }
 function reset(){cancelAnimationFrame(frame.current);surface.current.style.setProperty('--tilt-x','0deg');surface.current.style.setProperty('--tilt-y','0deg');}
 return <div className="fresh-landing" ref={surface} onPointerMove={move} onPointerLeave={reset}>
  <div className="fresh-glow" aria-hidden="true"/>
  <section className="fresh-hero">
   <div className="fresh-copy">
    <div className="fresh-eyebrow"><span/>A FRESH START FOR EVERY TICKET</div>
    <h1>Less waiting.<br/>More <span>understanding.</span></h1>
    <p>A clearer desk for every customer message. Fresh Desk suggests the issue, urgency, and support team—with people in the loop when a ticket needs care.</p>
    <div className="fresh-actions"><button className="fresh-start" onClick={onStart}>Open your desk <span>↗</span></button><button className="fresh-secondary" onClick={onModels}>Meet the models <span>→</span></button></div>
    <div className="fresh-trust"><span><i/>Locally trained models</span><span>සිංහල · தமிழ் · English</span></div>
   </div>
   <div className="fresh-demo" aria-label="Illustration of ticket classification and support review">
    <div className="fresh-orbit" aria-hidden="true"/><div className="fresh-orbit orbit-two" aria-hidden="true"/>
    <div className="fresh-float float-message"><span className="fresh-tile">✉</span><div><small>A customer message</small><strong>“My order hasn't arrived.”</strong></div><span className="fresh-dot"/></div>
    <div className="fresh-model-card"><div className="fresh-card-top"><span className="fresh-symbol">f<span>✳</span></span><span>FRESH DESK / EXAMPLE FLOW</span><i/></div><h2>From message<br/>to a next step.</h2><div className="fresh-models"><span>01 <b>Main issue</b></span><span>02 <b>Second concern</b></span><span>03 <b>Urgency</b></span></div><div className="fresh-route"><span>Suggested team</span><strong>Delivery Operations <i>↗</i></strong></div><div className="fresh-signal"><span/><span/><span/><span/><span/><span/><span/><span/><span/><span/><span/><span/><span/><span/><span/></div><p>3 trained classifiers. One clear workspace.</p></div>
    <div className="fresh-float float-review"><span className="fresh-tile review-tile">✓</span><div><small>When confidence is low</small><strong>A person takes a closer look.</strong></div></div>
    <span className="fresh-spark spark-a" aria-hidden="true">✳</span><span className="fresh-spark spark-b" aria-hidden="true">✦</span>
   </div>
  </section>
  <section className="fresh-facts" aria-label="Fresh Desk capabilities"><div><strong>3</strong><span>trained models</span></div><div><strong>11</strong><span>support routes</span></div><div><strong>5,000</strong><span>tickets per batch job</span></div><div><strong>Human</strong><span>review and acceptance</span></div></section>
  <section className="fresh-process"><div className="fresh-section-heading"><p className="kicker">A little clarity goes a long way</p><h2>A good handoff starts here.</h2><p>One workspace for messages, model signals, and support decisions.</p></div><div className="fresh-feature-grid">{[['01','Send it in','Chat, email, or call transcript. Start with one ticket or bring a JSON batch.','↗'],['02','See the signals','Inspect issue candidates, urgency probability, and the reason a ticket needs review.','⌁'],['03','Keep people involved','The support role reviews uncertain or urgent tickets and accepts the final team.','◇']].map(([n,title,text,icon])=><article key={n}><div><span>{n}</span><b>{icon}</b></div><h3>{title}</h3><p>{text}</p></article>)}</div></section>
  <section className="fresh-support-cta"><div><p className="kicker">For your support team</p><h2>A shared queue.<br/>A thoughtful decision.</h2><p>Review the message and model details, confirm a route, and save acceptance for the customer to see.</p></div><button onClick={onSupport}>Enter support workspace <span>↗</span></button></section>
 </div>;
}
