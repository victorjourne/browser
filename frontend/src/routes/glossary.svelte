<svelte:head>
	<title>Rechercher</title>
</svelte:head>

<script>
	import { onMount } from 'svelte';

	import Synonym from '../components/synonym/Synonym.svelte';

	let meta = [
						{
							key: 'expressionA',
							type: 'text',
							placeholder: 'DNUM',
							value: '',
							innerHtml: 'Acronyme: ',
							size: '1/5'
						},
						{
							key: 'expressionB',
							type: 'text',
							placeholder: 'Direction du Numérique',
							value: '',
							innerHtml: 'Signification: ',
							size: '4/5'
						}
					]


</script>

<Synonym meta={meta} filename='glossaire' />
