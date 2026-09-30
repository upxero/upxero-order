export function EmptyState({ icon: Icon, title, description, action, testid }) {
  return (
    <div
      className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center"
      data-testid={testid}
    >
      {Icon && (
        <span className="mb-4 grid h-12 w-12 place-items-center rounded-full bg-slate-100 text-slate-400">
          <Icon className="h-6 w-6" />
        </span>
      )}
      <h3 className="font-heading text-base font-semibold text-slate-900">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
