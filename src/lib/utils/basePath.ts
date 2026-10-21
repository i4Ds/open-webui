// Sub path support (WEBUI_BASE_PATH). The build uses base "", the backend
// writes the real base into index.html's SvelteKit bootstrap at runtime, so
// `base` here is e.g. "/planet-express" behind a proxy and "" otherwise
// (then everything below is a no-op).
import { base } from '$app/paths';

const isRootRelative = (url: string) => url.startsWith('/') && !url.startsWith('//');

const hasBase = (url: string) =>
	url === base ||
	url.startsWith(`${base}/`) ||
	url.startsWith(`${base}?`) ||
	url.startsWith(`${base}#`);

/** "/c/123" -> "/planet-express/c/123"; already prefixed, relative or absolute URLs are returned unchanged. */
export const withBase = (url: string): string => {
	if (!base || typeof url !== 'string' || !isRootRelative(url) || hasBase(url)) {
		return url;
	}
	return `${base}${url}`;
};

/** "/planet-express/c/123" -> "/c/123", for comparing the current path with app routes. */
export const stripBase = (pathname: string): string => {
	if (!base || typeof pathname !== 'string' || !hasBase(pathname)) {
		return pathname;
	}
	return pathname.slice(base.length) || '/';
};

const SAME_ORIGIN_ATTRS = ['src', 'href', 'poster'];

const fixElement = (el: Element) => {
	for (const attr of SAME_ORIGIN_ATTRS) {
		const value = el.getAttribute(attr);
		if (value && isRootRelative(value) && !hasBase(value)) {
			el.setAttribute(attr, withBase(value));
		}
	}
};

/**
 * Safety net for root-relative URLs the code can't know about in advance:
 * URLs from backend data (profile images, files in chat messages, model
 * metadata) and placeholders set on the fly. Rewrites fetch/XHR/EventSource
 * targets and src/href/poster attributes in the DOM.
 */
export const installBasePathShims = () => {
	if (!base || typeof window === 'undefined' || (window as any).__basePathShims) {
		return;
	}
	(window as any).__basePathShims = true;

	const originalFetch = window.fetch.bind(window);
	window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
		if (typeof input === 'string') {
			input = withBase(input);
		} else if (input instanceof URL) {
			if (input.origin === location.origin && !hasBase(input.pathname)) {
				input = new URL(withBase(input.pathname) + input.search + input.hash, input.origin);
			}
		} else if (input instanceof Request) {
			const url = new URL(input.url);
			if (url.origin === location.origin && !hasBase(url.pathname)) {
				input = new Request(withBase(url.pathname) + url.search + url.hash, input);
			}
		}
		return originalFetch(input, init);
	};

	const originalOpen = XMLHttpRequest.prototype.open;
	XMLHttpRequest.prototype.open = function (method: string, url: string | URL, ...rest: any[]) {
		return (originalOpen as any).call(
			this,
			method,
			typeof url === 'string' ? withBase(url) : url,
			...rest
		);
	} as typeof XMLHttpRequest.prototype.open;

	const OriginalEventSource = window.EventSource;
	if (OriginalEventSource) {
		window.EventSource = class extends OriginalEventSource {
			constructor(url: string | URL, init?: EventSourceInit) {
				super(typeof url === 'string' ? withBase(url) : url, init);
			}
		} as typeof EventSource;
	}

	const fixTree = (node: Node) => {
		if (!(node instanceof Element)) return;
		fixElement(node);
		node.querySelectorAll('[src^="/"],[href^="/"],[poster^="/"]').forEach(fixElement);
	};

	const observer = new MutationObserver((mutations) => {
		for (const m of mutations) {
			if (m.type === 'attributes') {
				fixElement(m.target as Element);
			} else {
				m.addedNodes.forEach(fixTree);
			}
		}
	});
	observer.observe(document.documentElement, {
		subtree: true,
		childList: true,
		attributes: true,
		attributeFilter: SAME_ORIGIN_ATTRS
	});
	fixTree(document.documentElement);
};
