import {Fragment,useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';

const media=query=>typeof window!=='undefined'&&window.matchMedia(query).matches;
export const prefersReducedMotion=()=>media('(prefers-reduced-motion: reduce)');

// Headline words that rise into place; `start` continues the stagger across lines.
export function Words({text,start=0}) {
 return text.split(' ').map((word,i)=><Fragment key={i}><span className="fresh-word" style={{'--i':start+i}}><span>{word}</span></span>{' '}</Fragment>);
}

// Animates a number toward its latest value.
export function Count({value}) {
 const [shown,setShown]=useState(value),from=useRef(value);
 useEffect(()=>{
  if(prefersReducedMotion()||from.current===value){from.current=value;setShown(value);return;}
  const start=from.current,begin=performance.now();let frame;
  const tick=now=>{const p=Math.min((now-begin)/700,1),next=Math.round(start+(value-start)*(1-Math.pow(1-p,3)));setShown(next);from.current=next;if(p<1)frame=requestAnimationFrame(tick);};
  frame=requestAnimationFrame(tick);
  return()=>cancelAnimationFrame(frame);
 },[value]);
 return shown.toLocaleString();
}

const SPOT='[data-spot],.panel,.metric-card',MAGNET='[data-magnetic],.btn';

// Pointer layer shared by every page: cursor ring, spotlight cards, magnetic buttons, and parallax variables.
export default function FreshSurface({children,className=''}) {
 const surface=useRef(null),frame=useRef(0),ring=useRef(null),ringFrame=useRef(0),magnet=useRef(null);
 const ringPos=useRef({x:0,y:0,tx:0,ty:0,live:false});
 const [fine]=useState(()=>media('(pointer: fine)')&&!prefersReducedMotion());

 useEffect(()=>()=>{cancelAnimationFrame(frame.current);cancelAnimationFrame(ringFrame.current);},[]);

 function stepRing() {
  const p=ringPos.current;
  p.x+=(p.tx-p.x)*.2;p.y+=(p.ty-p.y)*.2;
  if(ring.current)ring.current.style.transform=`translate3d(${p.x}px,${p.y}px,0)`;
  ringFrame.current=Math.abs(p.tx-p.x)+Math.abs(p.ty-p.y)>.15?requestAnimationFrame(stepRing):0;
 }

 function move(event) {
  if(!fine||event.pointerType==='touch')return;
  const {clientX:cx,clientY:cy}=event,target=event.target,p=ringPos.current;
  p.tx=cx;p.ty=cy;
  if(!p.live){p.x=cx;p.y=cy;p.live=true;}
  if(!ringFrame.current)ringFrame.current=requestAnimationFrame(stepRing);
  const hover=target.closest?.('button:not(:disabled),a,label,select,[data-cursor]');
  const typing=target.closest?.('input,textarea');
  if(ring.current){
   ring.current.classList.add('is-visible');
   ring.current.classList.toggle('is-hover',!!hover&&!typing);
   ring.current.classList.toggle('is-text',!!typing);
   ring.current.dataset.label=hover?.dataset.cursor||'';
  }

  const spot=target.closest?.(SPOT);
  if(spot){const b=spot.getBoundingClientRect();spot.style.setProperty('--x',`${cx-b.left}px`);spot.style.setProperty('--y',`${cy-b.top}px`);}
  const pull=target.closest?.(MAGNET);
  const active=pull&&!pull.disabled?pull:null;
  if(magnet.current&&magnet.current!==active)magnet.current.style.translate='';
  magnet.current=active;
  if(active){const b=active.getBoundingClientRect();active.style.translate=`${(cx-b.left-b.width/2)*.22}px ${(cy-b.top-b.height/2)*.35}px`;}

  cancelAnimationFrame(frame.current);
  frame.current=requestAnimationFrame(()=>{
   const style=surface.current.style;
   style.setProperty('--cursor-x',`${cx}px`);style.setProperty('--cursor-y',`${cy}px`);
   style.setProperty('--mx',(cx/innerWidth-.5)*2);style.setProperty('--my',(cy/innerHeight-.5)*2);
  });
 }

 function leave() {
  cancelAnimationFrame(frame.current);
  ringPos.current.live=false;
  ring.current?.classList.remove('is-visible','is-hover','is-down','is-text');
  if(magnet.current){magnet.current.style.translate='';magnet.current=null;}
  surface.current.style.setProperty('--mx',0);surface.current.style.setProperty('--my',0);
 }
 const press=down=>()=>ring.current?.classList.toggle('is-down',down);

 return <div className={`fresh-surface ${className}`} ref={surface} onPointerMove={move} onPointerLeave={leave} onPointerDown={press(true)} onPointerUp={press(false)}>
  {fine&&createPortal(<div className="fresh-cursor" ref={ring} aria-hidden="true"/>,document.body)}
  <div className="fresh-glow" aria-hidden="true"/>
  <div className="fresh-grid" aria-hidden="true"/>
  {children}
 </div>;
}
