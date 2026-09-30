export const euro = (value) =>
  new Intl.NumberFormat("nl-BE", { style: "currency", currency: "EUR" }).format(
    Number(value || 0)
  );

export const formatTime = (iso) => {
  try {
    return new Date(iso).toLocaleTimeString("nl-BE", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
};

export const formatDateTime = (iso) => {
  try {
    return new Date(iso).toLocaleString("nl-BE", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
};
