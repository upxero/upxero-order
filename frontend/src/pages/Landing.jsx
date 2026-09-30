import { Link } from "react-router-dom";
import { ArrowRight, Check, Percent, Smartphone, Truck } from "lucide-react";
import { Logo } from "../components/Logo";
import { Button } from "../components/ui/button";

export default function Landing() {
  return (
    <div className="min-h-screen bg-white">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Logo />
        <div className="flex items-center gap-3">
          <Link to="/login">
            <Button variant="ghost" className="text-slate-700" data-testid="landing-login-button">Inloggen</Button>
          </Link>
          <Link to="/registreren">
            <Button className="bg-emerald-600 hover:bg-emerald-700" data-testid="landing-register-button">
              Start gratis
            </Button>
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 pb-8 pt-10 lg:pt-20">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
              <Percent className="h-3.5 w-3.5" /> 0% commissie
            </span>
            <h1 className="mt-5 font-heading text-4xl font-extrabold leading-tight tracking-tight text-slate-900 sm:text-5xl">
              Online bestellen voor jouw restaurant, <span className="text-emerald-600">zonder commissie</span>.
            </h1>
            <p className="mt-5 max-w-lg text-base text-slate-600 sm:text-lg">
              Upxero Ordering geeft je een eigen bestelpagina voor afhalen en bezorgen. Beheer je menu, stel
              bezorgzones in en volg bestellingen live — vanaf elk toestel.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/registreren">
                <Button size="lg" className="bg-emerald-600 hover:bg-emerald-700" data-testid="landing-cta-register">
                  Registreer je restaurant <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link to="/order/bistro-demo">
                <Button size="lg" variant="outline" className="border-slate-300" data-testid="landing-demo-button">
                  Bekijk demo-bestelpagina
                </Button>
              </Link>
            </div>
            <ul className="mt-8 grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
              {["Geen commissie per bestelling", "Afhalen én bezorgen", "Eigen bestellink & QR", "Werkt op elk toestel"].map((t) => (
                <li key={t} className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-emerald-600" /> {t}
                </li>
              ))}
            </ul>
          </div>
          <div className="relative">
            <img
              src="https://images.pexels.com/photos/31176091/pexels-photo-31176091.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
              alt="Burger en frietjes"
              className="aspect-[4/3] w-full rounded-2xl object-cover shadow-xl"
            />
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-4 px-6 py-12 sm:grid-cols-3">
        {[
          { icon: Percent, title: "Commissievrij", desc: "Je houdt elke euro van je bestellingen." },
          { icon: Truck, title: "Slimme bezorging", desc: "Bezorgzones op afstand met eigen tarieven en minimumbedragen." },
          { icon: Smartphone, title: "Mobiel eerst", desc: "Klanten bestellen in enkele taps via link of QR-code." },
        ].map(({ icon: Icon, title, desc }) => (
          <div key={title} className="rounded-xl border border-slate-200 bg-white p-6">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-emerald-50 text-emerald-600">
              <Icon className="h-5 w-5" />
            </span>
            <h3 className="mt-4 font-heading text-base font-semibold text-slate-900">{title}</h3>
            <p className="mt-1 text-sm text-slate-500">{desc}</p>
          </div>
        ))}
      </section>

      <footer className="border-t border-slate-200 py-8 text-center text-sm text-slate-400">
        © {new Date().getFullYear()} Upxero Ordering
      </footer>
    </div>
  );
}
