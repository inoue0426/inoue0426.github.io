const toggle=document.querySelector('.nav-toggle');
const nav=document.querySelector('#site-nav');

if(toggle&&nav){
  toggle.addEventListener('click',()=>{
    const open=nav.classList.toggle('open');
    toggle.setAttribute('aria-expanded',String(open));
  });
  nav.querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>{
    nav.classList.remove('open');
    toggle.setAttribute('aria-expanded','false');
  }));
}

const heroCopy=document.querySelector('.hero-copy');
if(heroCopy&&!heroCopy.querySelector('.hero-portrait')){
  const text=document.createElement('div');
  text.className='hero-text';
  while(heroCopy.firstChild) text.appendChild(heroCopy.firstChild);

  const figure=document.createElement('figure');
  figure.className='hero-portrait';
  const image=document.createElement('img');
  image.src='assets/profile.jpg';
  image.alt='Portrait of Yoshitaka Inoue';
  image.width=320;
  image.height=320;
  image.loading='eager';
  image.decoding='async';
  figure.appendChild(image);

  heroCopy.appendChild(text);
  heroCopy.appendChild(figure);

  const style=document.createElement('style');
  style.textContent=`
    .hero-copy{max-width:none;display:grid;grid-template-columns:minmax(0,1fr) 210px;gap:4.5rem;align-items:center}
    .hero-text{min-width:0}
    .hero-portrait{margin:0;justify-self:end;width:190px}
    .hero-portrait img{display:block;width:190px;height:190px;object-fit:cover;object-position:center 30%;border-radius:50%;border:1px solid var(--line);filter:saturate(.9) contrast(.98);box-shadow:0 10px 30px rgba(20,35,60,.08)}
    @media(max-width:800px){
      .hero-copy{grid-template-columns:1fr;gap:2rem}
      .hero-portrait{grid-row:1;justify-self:start;width:126px}
      .hero-portrait img{width:126px;height:126px}
    }
  `;
  document.head.appendChild(style);
}

const year=document.querySelector('#year');
if(year){year.textContent=new Date().getFullYear();}
