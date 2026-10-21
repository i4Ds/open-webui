<script>
	import { goto } from '$lib/utils/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		goto('/admin/evaluations/leaderboard', { replaceState: true });
	});
</script>
