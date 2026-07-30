export function decodeHtmlEntities(value) {
	if (value === null || value === undefined) return '';

	return String(value)
		.replace(/&nbsp;|&#160;|&#xA0;/gi, ' ')
		.replace(/&amp;/gi, '&')
		.replace(/&quot;/gi, '"')
		.replace(/&#39;|&apos;/gi, "'")
		.replace(/&lt;/gi, '<')
		.replace(/&gt;/gi, '>')
		.replace(/&#(\d+);/g, function(match, code) {
			var value = Number(code);
			return Number.isFinite(value) ? String.fromCharCode(value) : match;
		})
		.replace(/&#x([0-9a-f]+);/gi, function(match, code) {
			var value = parseInt(code, 16);
			return Number.isFinite(value) ? String.fromCharCode(value) : match;
		})
		.replace(/\s+/g, ' ')
		.trim();
}

export function sanitizeArticleText(value, fallback) {
	var cleaned = decodeHtmlEntities(value);
	return cleaned || fallback || '';
}
