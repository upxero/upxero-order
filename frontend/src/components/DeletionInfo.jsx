import { useT } from "../context/I18nContext";

const RESTAURANT_DELETED = [
  "Menu-items en categorieën",
  "Geüploade bestanden (logo, menukaart, productfoto's)",
  "Openstaande personeelsuitnodigingen",
  "Contactgegevens, adres en bezorgzones van het restaurant",
  "Alle gebruikersaccounts van dit restaurant worden geanonimiseerd en uitgeschakeld",
];
const RESTAURANT_RETAINED = [
  "Bestelgeschiedenis met bestelnummers, producten en totalen (boekhoudkundige bewaarplicht)",
  "Klantnamen, telefoonnummers, e-mailadressen, bezorgadressen en opmerkingen op bestellingen worden geanonimiseerd",
  "Restaurantnaam en aanmaakdatum, en het auditlog",
];

function List({ title, items, tone, testid }) {
  const t = useT();
  return (
    <div data-testid={testid}>
      <p className={`text-sm font-semibold ${tone}`}>{t(title)}</p>
      <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-600">
        {items.map((i) => <li key={i}>{t(i)}</li>)}
      </ul>
    </div>
  );
}

export function DeletionInfo({ type, email }) {
  const t = useT();
  if (type === "account") {
    return (
      <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600" data-testid="deletion-info-account">
        {t("Het account van {email} wordt geanonimiseerd en uitgeschakeld. Het restaurant, het menu en de bestellingen blijven ongewijzigd.", { email })}
      </p>
    );
  }
  return (
    <div className="space-y-3 rounded-lg bg-slate-50 p-3">
      <List title="Wordt verwijderd" items={RESTAURANT_DELETED} tone="text-rose-700" testid="deletion-info-deleted" />
      <List title="Blijft bewaard" items={RESTAURANT_RETAINED} tone="text-slate-800" testid="deletion-info-retained" />
    </div>
  );
}
