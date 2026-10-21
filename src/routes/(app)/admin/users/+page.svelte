<script>
	import { goto } from '$lib/utils/navigation';
	import { onMount } from 'svelte';

	onMount(async () => {
		await goto('/admin/users/overview', { replaceState: true });
	});
</script>
