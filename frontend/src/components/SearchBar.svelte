<script>
	import { searchResults, suggestEntry,  index_name } from '../components/stores.js';
	import { config } from '../components/utils.js';

	import SearchInput from  '../components/SearchInput.svelte';

	let promiseSearch =  new Promise(()=>{});
	let promiseSuggest =  new Promise(()=>{});
	let getInit =  new Promise(()=>{});

	let searchList = []
	let item = {}

	async function init() {
		item = await config('item.json')
		searchList = await config('search.json')
		promiseSearch = await search()
		return searchList
	}

	// init variables
	getInit = init()

	let body; // searchList in dict format
	//let searchListList = searchListObject.entries(searchList)
	//console.log(searchListList)
	const format2ES = (item, query_list) => {
		let query_dic = {index_name: $index_name};
		let obj;
		let highlight_fields = item.inputs.filter(obj => obj.highlight).map(x => x.key)
		for (obj of query_list) {
			let clause = {}
			if (obj.value != "") {
				//highlight_fields.push(obj.fields)
				if (!(obj.bool in query_dic)) {
					query_dic[obj.bool] = []
				}
				clause = JSON.parse(JSON.stringify(obj.query).replace('\$value', obj.value))
				query_dic[obj.bool].push(clause)
			}
		}
		if (highlight_fields.length >0){
			query_dic["highlight"] = highlight_fields.flat()
		}
		return query_dic
  };

	async function search() {
		body =  format2ES(item, searchList.flat(2))
		const res = await fetch("/api/common/search",{
												method: "POST",
												body: JSON.stringify(body)
													 });

		const items = await res.json();
		if (res.ok) {
			$searchResults = items
			return items.hits.length;
		} else {
			throw new Error('Oups');
		}
	}


	async function suggest() {
		const res = await fetch("/api/common/suggest",{
												method: "POST",
												body: JSON.stringify({
															 index_name: $index_name,
															 content: searchList.content.value,
														 })
													 });

		const items = await res.json();
		//console.log(items)
		if (res.ok) {
			$suggestEntry = items
			return "ok";
		} else {
			throw new Error('Oups');
		}
	}

	function handleSearch() {
		promiseSearch = search();
	}

	function handleSuggest() {
		console.log('handleSuggest')
		promiseSuggest = suggest();
	}

	function handleSuggestChosen(v) {
		//searchList.content.value = e.target.innerHTML
		searchList.content.value = v
		$suggestEntry = []
	}


</script>
<div class='search-bar'>
{#await getInit}
<p>...Initialisation</p>

{:then searchList}

	{#each searchList as row, i }
	<div class="flex mb-4">

		{#each row as {bool, query, value, type, placeholder, innerHtml, style}, j}
			{#if (i === 0) && (j === 0) }
				<div class="w-1/6 p-2" >
					<button on:click={handleSearch} class="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-6 rounded inline-flex items-center">
						<svg class="fill-current w-4 h-4 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M12.9 14.32a8 8 0 1 1 1.41-1.41l5.35 5.33-1.42 1.42-5.33-5.34zM8 14A6 6 0 1 0 8 2a6 6 0 0 0 0 12z"/></svg>
						<span>Rechercher</span>
					</button>
				</div>
			{/if}

			<SearchInput bind:value={value} {type} {placeholder} {innerHtml} {style} />
		{/each}
		</div>

	{/each}
	{/await}

{#await promiseSearch}
	<p>...Attente de la requête</p>

{:then length}
	<p>{length} documents trouvés</p>

{:catch error}
	<p style="color: red">{error.message}</p>
{/await}

</div>
<!--
<div class='search-bar'>

	<div class="flex mb-4">
		<div class="w-3/4 p-2" >
			<div class="flex flex-col px-2">
				<div class="px-2" >
				<label> {@html searchList.content.innerHtml}
					<input type="search" bind:value={searchList.content.value}
					       placeholder={searchList.content.placeholder}
								 on:input={handleSuggest}
								 class="bg-white focus:outline-none focus:shadow-outline border border-gray-300 rounded-lg py-2 px-4 block w-full appearance-none leading-normal">

				<div class="px-2" id="suggest">
					{#each $suggestEntry as {text, highlighted} }
				     <div class="bg-white hover:bg-gray-500" on:click="{e => handleSuggestChosen(text)}">
						 	{@html highlighted}
						 </div>
					 {/each}
				</div>
				</label>
				</div>

			<div class="flex mb-4">
				{#if searchList.author}
					<div class="w-2/4 px-2">
						<label> {@html searchList.author.innerHtml}
							<input type="search" bind:value={searchList.author.value}
										 placeholder={searchList.author.placeholder}
										class="bg-white focus:outline-none focus:shadow-outline border border-gray-300 rounded-lg py-2 px-4 block w-full appearance-none leading-normal">
						</label>
					</div>
				{/if}

				<div class="w-1/4 px-2" >
				<label> {@html searchList.from_date.innerHtml}
					<input type="date" bind:value={searchList.from_date.value}
					       placeholder={searchList.from_date.placeholder}
								  class="bg-white focus:outline-none focus:shadow-outline border border-gray-300 rounded-lg py-2 px-4 block w-full appearance-none leading-normal">
				</label>
				</div>
				<div class="w-1/4 px-2" >
					<label> {@html searchList.to_date.innerHtml}
						<input type="date" bind:value={searchList.to_date.value}
									 placeholder={searchList.to_date.placeholder}
										class="bg-white focus:outline-none focus:shadow-outline border border-gray-300 rounded-lg py-2 px-4 block w-full appearance-none leading-normal">
					</label>
				</div>
			</div>

			</div>

		</div>
		<div class="w-1/4 px-2" >
			<button on:click={handleSearch} class="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded inline-flex items-center">
				<svg class="fill-current w-4 h-4 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M12.9 14.32a8 8 0 1 1 1.41-1.41l5.35 5.33-1.42 1.42-5.33-5.34zM8 14A6 6 0 1 0 8 2a6 6 0 0 0 0 12z"/></svg>
				<span>Rechercher</span>
			</button>
		</div>

	</div>

	{#if searchList.content.value!=''}
		<h1>La recherche est : {searchList.content.value}</h1>
	{/if}

	{#await promiseSearch}
		<p>...Attente de la requête</p>

	{:then length}
		<p>{length} documents trouvés</p>

	{:catch error}
		<p style="color: red">{error.message}</p>
	{/await}

</div>
 //-->
<style>
	.search-bar {
		width: 100%;
		border: 1px solid #aaa;
		border-radius: 4px;
		box-shadow: 2px 2px 8px rgba(0,255,0,1);
		padding: 1em;
		margin: 0 0 1em 0;
	}

	#suggest {
			z-index: 2;
			position: absolute;
			background-color: rgba(255,255,255,1);
		}
	</style>
