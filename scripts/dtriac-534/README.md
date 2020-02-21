# Building the index

### Data processing

To process the data we first ran Science Parse over the pdf files and translated the output into LIF. We then ran the following tools:

- Python gensim topic extraction, an LDA model
- Tarsqi toolkit
- Reverb relation extraction
- Sentence classifier, to distinguish between normal sentences and crap sentences (references and formulas)
- Stanford NER
- FUSE/TechWatch technology extraction
- ClearWSD to assign VerbNet classes

### Creating the index

To build the index all information is merged (easy because it is LIF) and several fields (facets) are created.

The **text** field is taken straight from the LIF text and loaded into the index in the standard way, which means that there is no lemmatization (so to find both 'communication' and 'communications' you will have to do two queries or do 'OR communication communications').

The **topic** field comes from the Python gensim package, each topic is a sequence of lemmas, for example "system network power social node control failure given smart hybrid". Each document is associated with a list of topics. For visualization purposes there is also a field **topic_element** and its value is the list of all lemmas in the topics (with duplicates removed). There are a few other metadata fields that either come from Science Parse or from the name of the source file, namely **author**, **title** and **docname**.

The **event** and **time** fields are taken straight from Tarsqi, the latter is not very informative and as a result timestamps weren't added. From Stanford NER, the **person**, **location** and **organzation** fields are taken, other named entity types like NUMBER are ignored. The **technology** field comes from TechWatch, but goes through some extra processing by using an ontology of technology terms. This ontology is used to add known technologies that may not have been recognized by TechWatch. One example is 'Markov chain'. The ontology also can include negative examples like 'well-defined concepts' that can be used as a stoplist.

Finally, the relation fields (**relation.pred**, **relation.arg1** and **relation.arg2**) are taken from ReVerb. But since ReVerb overgeneralizes dramatically, the relations are filtered by only allowing relations where the predicate includes an event and one of the arguments includes a technology or named entity. We intended to add a VerbNet class as well, but ran out of time to fix a few bugs in the code that merges in VerbNet classes.

For each document a JSON object is put in the **demo_document_479** index. The number 479 reflects the number of documents remaining from the original 534 after processing. Some documents were taken out because they were too big (for example a 20MB dissertation), some because some component crashed on the document or produced unwellformed output and some because the index creation code failed. Issues with the index creation code could not be fixed in time for the demo.

Here is a fragment of a document.

```
{
    "docid": "0001",
    "docname": "16. Modeling Impact of Communication-Network Failures on Power-Grid Reliability",
    "text": "......",
    "title": "Modeling Impact of Communication Network Failures on Power Grid Reliability",
    "author": ["Rezoan A. Shuvro", "Zhuoyao Wang", "Pankaz Das"],
    "topic": [
        "network node degree percolation attack random function fraction distribution component",
        "power system vertex services service communication model provide represent domain"],
    "topic_element": [
        "attack", "communication", "component", "degree", "distribution", ...],
    "event": ["play", "delivery", "stressed",  "failures", ... ],
    "time": ["2003", "Now"],
    "location": ["United States", "Canada", "Italy"],
    "organization": ["GW", "SASE", "IDMC", "Defense Threat Reduction Agency"],
    "person": ["Markov", "Carreras", "Wang"],
    "technology": [
        "analytical model", "communication node", "communication system", "communication-node failures",
        "control center", "human operators", "key attributes", "markov chain", ...],
    "relation": [
        {"arg1": "Carreras et al",
         "arg2": "coupling",
         "pred": "investigated the effect of"}, ...]
}
```

In addition to the documents index another index named **demo_sentences_479** is created for sentences. When a document matches a query the document is returned with some of its contents as specified in the original query, but what is not returned is the location of the text that matched or the location in the text where a facet was expressed. For example, if we search for location=Italy the above document will match because Italy is listed under location, but we do not know where in the text Italy is.

In order to quickly find occurrences in sentences the sentence index was created. This index does not contain the metadata but has those fields that do occur in a sentence:

```
{
    "docid": "0030",
    "sentid": "0016",
    "event": [ "contributed", "failed", "leaving"],
    "technology": ["human operators"],
    "text": "Specifically, the alarm software failed leaving the human operators unaware of the transmission-line outage which contributed the cascading-failure [1]."
}
```

Only sentences that are marked as normal are included in this index.

Tow alternatives to creating the sentence index were considered:

1. Return the entire text field and do a search on this. Non optimal because you end up returning large amounts of data on some queries.

2. Maintain a separate index apart from the ElasticSearch index. For future flexibility this may be a good way to go but it seemed redundant at the moment. This index could contain the LIF object for each document.


### Querying

Any query entered in the search box, whether it is on the text field or one of the other specialized fields, is applied to the document index.

A query matches a document if all fields/facets of the query match the document (unless the query is an OR query). ElasticSearch returns these documents ordered by a relevance score, even if there are more hits only the top 20 will be returned (this is a hard-coded setting, it is changed for the "list all documents" link on the home page).

For each document, a new set of queries is constructed and that set is applied to the sentence index. For example, let's start with the search query

```
AND person:markov location:Italy
```

and assume it returns two documents '0011' and '0017'. The new set of queries for document '0011' will be

```
AND docid:0011 person:markov
AND docid:0011 location:Italy
```
This effectively gets all sentences in document '0011' that have 'markov' or 'Italy'. Restricting this to an AND would be too strict. All the sentences will be filtered by removing duplicates and then ordered on relevance score.

Ideally we would want to use

```
docid:0011 AND (person:markov OR location:Italy)
```

but the query language does not yet allow that.

Searches are case-insensitive, both 'Markov' and 'markov' give the same results, and so do 'location:Italy' and 'location:italy'.
