<script>
	import { goto } from '$lib/utils/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		goto('/?settings=admin%3Ageneral', { replaceState: true });
	});
</script>
