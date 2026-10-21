import { installBasePathShims } from '$lib/utils/basePath';

// Before any page code runs: keep root-relative URLs under WEBUI_BASE_PATH.
installBasePathShims();
