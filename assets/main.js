const toggle=document.querySelector('.nav-toggle');
const nav=document.querySelector('#site-nav');
if(toggle&&nav){
  toggle.addEventListener('click',()=>{
    const open=nav.classList.toggle('open');
    toggle.setAttribute('aria-expanded',String(open));
  });
  nav.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{
    nav.classList.remove('open');
    toggle.setAttribute('aria-expanded','false');
  }));
}

const cvUrl='https://docs.google.com/document/d/1MhDXdLBmyeCmtZ9Nl2uiqMtoHrTNxi1p/edit?usp=sharing&ouid=106112363458944521656&rtpof=true&sd=true';

const profileLinks=document.querySelector('.profile-links');
if(profileLinks&&!profileLinks.querySelector('[data-cv-link]')){
  const item=document.createElement('li');
  const link=document.createElement('a');
  link.href=cvUrl;
  link.textContent='CV';
  link.target='_blank';
  link.rel='noopener';
  link.dataset.cvLink='true';
  item.appendChild(link);
  profileLinks.insertBefore(item,profileLinks.children[1]||null);
}

const contactActions=document.querySelector('#contact .actions');
if(contactActions&&!contactActions.querySelector('[data-cv-link]')){
  const link=document.createElement('a');
  link.className='button';
  link.href=cvUrl;
  link.textContent='View CV';
  link.target='_blank';
  link.rel='noopener';
  link.dataset.cvLink='true';
  contactActions.appendChild(link);
}

const year=document.querySelector('#year');
if(year){year.textContent=new Date().getFullYear();}
