import { Link } from "react-router-dom";
import { ArrowRight, Check, Percent, Smartphone, Truck } from "lucide-react";
import { HomeLogo } from "../components/AuthTopBar";
import { LangToggle } from "../components/LangToggle";
import { PublicFooter } from "../components/PublicFooter";
import { Button } from "../components/ui/button";
import { makeT } from "../lib/i18n";
import { usePublicLang } from "../lib/publicLang";

const BULLETS = ["Geen commissie per bestelling", "Afhalen en bezorgen", "Eigen bestellink & QR", "Werkt op elk apparaat"];
const FEATURES = [
  { icon: Percent, title: "Zonder commissie", desc: "Je houdt elke euro van je bestellingen." },
  { icon: Truck, title: "Slimme bezorging", desc: "Bezorgzones op afstand met je eigen tarieven en minimumbedragen." },
  { icon: Smartphone, title: "Mobiel eerst", desc: "Klanten bestellen in een paar tikken via link of QR-code." },
];

export default function Landing() {
  const [lang, setLang] = usePublicLang();
  const t = makeT(lang);
  return (
    <div className="min-h-screen bg-white">
      <header className="mx-auto flex max-w-6xl items-center justify-between gap-2 px-4 py-5 sm:px-6">
        <HomeLogo className="hidden sm:flex" />
        <HomeLogo compact className="sm:hidden" />
        <div className="flex items-center gap-2 sm:gap-3">
          <LangToggle lang={lang} setLang={setLang} />
          <Link to="/login">
            <Button variant="ghost" className="px-2 text-slate-700 sm:px-4" data-testid="landing-login-button">{t("Inloggen")}</Button>
          </Link>
          <Link to="/registreren">
            <Button className="bg-emerald-600 px-3 hover:bg-emerald-700 sm:px-4" data-testid="landing-register-button">
              {t("Gratis starten")}
            </Button>
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 pb-8 pt-10 lg:pt-20">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
              <Percent className="h-3.5 w-3.5" /> {t("0% commissie")}
            </span>
            <h1 className="mt-5 font-heading text-4xl font-extrabold leading-tight tracking-tight text-slate-900 sm:text-5xl" data-testid="landing-title">
              {t("Online bestellen voor je restaurant,")} <span className="text-emerald-600">{t("zonder commissie")}</span>.
            </h1>
            <p className="mt-5 max-w-lg text-base text-slate-600 sm:text-lg">
              {t("Upxero Ordering geeft je een eigen bestelpagina voor afhalen en bezorgen. Beheer je menu, stel bezorgzones in en volg bestellingen live — vanaf elk apparaat.")}
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/registreren">
                <Button size="lg" className="bg-emerald-600 hover:bg-emerald-700" data-testid="landing-cta-register">
                  {t("Registreer je restaurant")} <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link to="/order/bistro-demo">
                <Button size="lg" variant="outline" className="border-slate-300" data-testid="landing-demo-button">
                  {t("Bekijk demo-bestelpagina")}
                </Button>
              </Link>
            </div>
            <ul className="mt-8 grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
              {BULLETS.map((b) => (
                <li key={b} className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-emerald-600" /> {t(b)}
                </li>
              ))}
            </ul>
          </div>
          <div className="relative">
            <img
              src="https://images.pexels.com/photos/31176091/pexels-photo-31176091.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
              alt="Burger and fries"
              className="aspect-[4/3] w-full rounded-2xl object-cover shadow-xl"
            />
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-4 px-6 py-12 sm:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, desc }) => (
          <div key={title} className="rounded-xl border border-slate-200 bg-white p-6">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-emerald-50 text-emerald-600">
              <Icon className="h-5 w-5" />
            </span>
            <h3 className="mt-4 font-heading text-base font-semibold text-slate-900">{t(title)}</h3>
            <p className="mt-1 text-sm text-slate-500">{t(desc)}</p>
          </div>
        ))}
      </section>

      <PublicFooter lang={lang} />
    </div>
  );
}
