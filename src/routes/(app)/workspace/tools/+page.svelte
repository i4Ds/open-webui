<script>
	import { onMount } from 'svelte';
	import { goto } from '$lib/utils/navigation';
	import { config } from '$lib/stores';

	import Tools from '$lib/components/workspace/Tools.svelte';

	onMount(() => {
		if (!$config?.features?.enable_tools) {
			goto('/workspace', { replaceState: true });
		}
	});
</script>

{#if $config?.features?.enable_tools}
	<Tools />
{/if}
