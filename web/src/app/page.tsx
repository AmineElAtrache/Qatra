import Link from "next/link";
import { ArrowRight, Check, CloudSun, Droplets, Layers3, MapPinned, MessageCircleQuestion, Play, Satellite, ShieldCheck, Sprout } from "lucide-react";
import Logo from "@/components/ui/Logo";
import { CONTRACT_SAMPLE } from "@/lib/sample";
import s from "./home.module.css";

const steps = [
  { icon: MapPinned, title: "Délimitez votre parcelle", text: "Dessinez les contours de votre parcelle sur la carte interactive." },
  { icon: Sprout, title: "Renseignez votre culture", text: "Précisez le stade de vos agrumes et votre méthode d’irrigation." },
  { icon: CloudSun, title: "Croisez les données", text: "Météo et observations satellitaires disponibles éclairent le calcul." },
  { icon: Droplets, title: "Décidez avec clarté", text: "Consultez le besoin estimé, son explication et les points à vérifier." },
];

export default function HomePage() {
  return <div className={s.home}>
    <a className={s.skip} href="#contenu">Aller au contenu</a>
    <header className={s.header}><div className={s.navbar}>
      <Link href="/" className={s.brand} aria-label="Qatra, accueil"><Logo size={31} />Qatra<span>.</span></Link>
      <nav className={s.nav} aria-label="Navigation principale"><a href="#solution">La solution</a><a href="#fonctionnalites">Fonctionnalités</a><a href="#comment">Comment ça marche</a></nav>
      <div className={s.actions}><Link href="/login" className={s.login}>Se connecter</Link><Link href="/register" className={s.primary}>Commencer <ArrowRight size={16} /></Link></div>
    </div></header>
    <main id="contenu">
      <section id="solution" className={s.hero}><div className={s.heroInner}>
        <div><span className={s.eyebrow}><span /> POUR UNE AGRICULTURE PLUS RAISONNÉE</span><h1>L’eau juste,<br /><em>parcelle par<br className={s.desktopBreak} /> parcelle.</em></h1><p className={s.intro}>Vos agrumes ont des besoins précis. Qatra vous aide à les comprendre, grâce à la météo, aux données satellite disponibles et à la méthode FAO-56.</p>
          <div className={s.heroActions}><Link href="/register" className={s.primary}>Créer mon compte <ArrowRight size={18} /></Link><Link href="/demo" className={s.secondary}><Play size={16} /> Voir la démonstration</Link></div>
          <p className={s.note}><ShieldCheck size={15} /> Pensé pour les agriculteurs et conseillers au Maroc</p>
        </div>
        <div className={s.visual}>
          <span className={s.visualTag}>● VOTRE PARCELLE, MIEUX COMPRISE</span>
          <div className={s.boundary} aria-hidden="true"><span>{CONTRACT_SAMPLE.plot_id}</span></div>
          <div className={s.estimate}><Droplets size={27} /><div><span>Besoin en eau · ETc</span><strong>{CONTRACT_SAMPLE.etc_mm?.toLocaleString("fr-FR") ?? "—"} <small>mm / jour</small></strong><p>Exemple illustratif · agrumes</p></div></div>
          <div className={s.caption}><Sprout size={20} /><span>Des données à la décision.<br /><strong>Au plus près de vos cultures.</strong></span></div>
        </div>
      </div></section>
      <section className={s.benefits} aria-label="Les atouts de Qatra">{[{ icon: Droplets, title: "Une estimation scientifique", text: "Les besoins en eau calculés selon FAO-56." }, { icon: Layers3, title: "Des données complémentaires", text: "Météo, culture et observations satellitaires." }, { icon: ShieldCheck, title: "Des décisions éclairées", text: "Des résultats expliqués et des limites visibles." }].map(({ icon: Icon, title, text }) => <div key={title}><Icon size={27} strokeWidth={1.6} /><div><h2>{title}</h2><p>{text}</p></div></div>)}</section>
      <section id="comment" className={s.how}><div className={s.heading}><span className={s.kicker}>SIMPLE SUR LE TERRAIN</span><h2>Votre parcelle. Vos données.<br />Une décision plus claire.</h2><p>De la carte au besoin en eau, Qatra vous accompagne à chaque étape.</p></div><div className={s.steps}>{steps.map(({ icon: Icon, title, text }, i) => <article key={title}><div className={s.stepTop}><span className={s.stepIcon}><Icon size={28} strokeWidth={1.5} /></span><span>0{i + 1}</span></div><h3>{title}</h3><p>{text}</p></article>)}</div></section>
      <section id="fonctionnalites" className={s.features}>
        <div className={s.dataVisual}><div className={s.dataHeading}><Logo size={24} /><strong>Les données de votre parcelle</strong><span>FAO-56</span></div>{[{ icon: MapPinned, title: "Parcelle & culture", text: "Contours, surface, stade des agrumes" }, { icon: CloudSun, title: "Météo & pluie", text: "Évapotranspiration et pluie utile" }, { icon: Satellite, title: "Observations satellite", text: "NDVI, NDWI et qualité des images" }].map(({ icon: Icon, title, text }) => <div className={s.dataRow} key={title}><span><Icon size={23} /></span><div><strong>{title}</strong><p>{text}</p></div><Check size={16} /></div>)}<div className={s.dataResult}><Droplets size={24} /><div><strong>Un besoin en eau expliqué</strong><p>Les données manquantes sont signalées.</p></div><ArrowRight size={19} /></div></div>
        <div className={s.featureCopy}><span className={s.kicker}>LA TECHNOLOGIE AU SERVICE DU TERRAIN</span><h2>Une vue d’ensemble.<br /><em>Pour chaque parcelle.</em></h2><p>Retrouvez les informations utiles au même endroit, avec des explications accessibles en français, en arabe et en darija.</p><ul><li><MapPinned size={18} /> Cartographie et suivi de vos parcelles</li><li><Droplets size={18} /> Besoin estimé et bilan d’irrigation</li><li><Satellite size={18} /> Indicateurs satellite, lorsqu’ils sont disponibles</li><li><MessageCircleQuestion size={18} /> Ask Qatra pour comprendre vos résultats</li></ul><Link href="/demo" className={s.textLink}>Explorer l’exemple MA-001 <ArrowRight size={17} /></Link></div>
      </section>
      <section className={s.cta}><div><span className={s.eyebrow}>CHAQUE GOUTTE COMPTE</span><h2>Mieux comprendre aujourd’hui.<br /><em>Mieux irriguer demain.</em></h2><p>Commencez par votre première parcelle.</p></div><Link href="/register" className={s.primary}>Créer mon compte <ArrowRight size={18} /></Link></section>
    </main>
    <footer className={s.footer}><Link href="/" className={s.brand}><Logo size={25} />Qatra.</Link><p>L’intelligence des données. Le bon sens du terrain.</p><div><Link href="/demo">Démonstration</Link><Link href="/login">Se connecter</Link></div><small>Qatra · Aide à la décision agricole</small></footer>
  </div>;
}
