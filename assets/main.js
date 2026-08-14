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
if(heroCopy&&!heroCopy.querySelector('.hero-profile-card')){
  const text=document.createElement('div');
  text.className='hero-text';
  while(heroCopy.firstChild) text.appendChild(heroCopy.firstChild);

  const affiliation=text.querySelector('.affiliation');
  if(affiliation) affiliation.hidden=true;

  const card=document.createElement('aside');
  card.className='hero-profile-card';
  card.setAttribute('aria-label','Yoshitaka Inoue profile');
  card.innerHTML=`
    <img class="profile-photo" src="assets/profile.jpg" alt="Portrait of Yoshitaka Inoue" width="320" height="320" loading="eager" decoding="async">
    <h2>Yoshitaka Inoue</h2>
    <p><strong>PhD Candidate</strong><br>Computer Science and Engineering<br>University of Minnesota</p>
    <p><strong>Pre-doctoral Fellow</strong><br>National Library of Medicine / National Cancer Institute</p>
  `;

  heroCopy.appendChild(text);
  heroCopy.appendChild(card);

  const style=document.createElement('style');
  style.textContent=`
    .hero-copy{max-width:none;display:grid;grid-template-columns:minmax(0,1fr) 270px;gap:4rem;align-items:center}
    .hero-text{min-width:0}
    .hero-profile-card{margin:0;justify-self:end;width:270px;padding:1.25rem;border:1px solid var(--line);border-radius:.8rem;background:#fff;box-shadow:0 10px 30px rgba(20,35,60,.06)}
    .hero-profile-card .profile-photo{display:block;width:112px;height:112px;object-fit:cover;object-position:center 30%;border-radius:50%;margin:0 0 1rem;border:1px solid var(--line);filter:saturate(.9) contrast(.98)}
    .hero-profile-card h2{font-family:Georgia,"Times New Roman",serif;font-size:1.25rem;line-height:1.15;margin:.1rem 0 1rem}
    .hero-profile-card p{margin:.75rem 0 0;color:var(--muted);font-size:.88rem;line-height:1.5}
    .hero-profile-card strong{color:var(--text)}
    @media(max-width:800px){
      .hero-copy{grid-template-columns:1fr;gap:2rem}
      .hero-profile-card{justify-self:start;width:min(100%,360px)}
      .hero-profile-card .profile-photo{width:96px;height:96px}
    }
  `;
  document.head.appendChild(style);
}

const year=document.querySelector('#year');
if(year){year.textContent=new Date().getFullYear();}
