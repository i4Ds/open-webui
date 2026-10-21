// goto() that stays under the base path (WEBUI_BASE_PATH). The app navigates
// with root paths like goto('/c/123'); SvelteKit treats those as outside the
// app when a base is set and does a full page load to the wrong URL.
import { goto as svelteGoto } from '$app/navigation';
import { withBase } from '$lib/utils/basePath';

export const goto: typeof svelteGoto = (url, opts) =>
	svelteGoto(typeof url === 'string' ? withBase(url) : url, opts);
