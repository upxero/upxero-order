// Resolve a file reference returned by the API into a loadable URL.
// Absolute URLs (legacy image URLs) pass through unchanged; backend-relative
// paths (GridFS-served files) are prefixed with the backend origin.
export function resolveFileUrl(url) {
  if (!url) return "";
  if (/^https?:\/\//i.test(url) || url.startsWith("blob:") || url.startsWith("data:")) return url;
  return `${process.env.REACT_APP_BACKEND_URL}${url}`;
}

export function menuItemImageUrl(slug, itemId, fileId) {
  if (!slug || !itemId || !fileId) return "";
  return `${process.env.REACT_APP_BACKEND_URL}/api/public/restaurant/${slug}/menu-item/${itemId}/image?v=${fileId}`;
}

export function logoUrl(slug, fileId) {
  if (!slug || !fileId) return "";
  return `${process.env.REACT_APP_BACKEND_URL}/api/public/restaurant/${slug}/logo?v=${fileId}`;
}

export function menuFileUrl(slug, fileId) {
  if (!slug || !fileId) return "";
  return `${process.env.REACT_APP_BACKEND_URL}/api/public/restaurant/${slug}/menu-file?v=${fileId}`;
}
