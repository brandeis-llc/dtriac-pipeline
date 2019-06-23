from flask import Flask, render_template, request
from pprint import pformat

from utils.elastic import Index, Source
from utils.query import query
from utils.misc import get_var, Statistics, Kibana


INDEX_DOC = Index('demo_documents')
INDEX_SEN = Index('demo_sentences')

STATS_FILE = 'data/stats.json'


app = Flask(__name__)


@app.route("/")
def index():
    stats = Statistics(STATS_FILE)
    kibana = Kibana()
    return render_template("index.html", stats=stats, kibana=kibana)


@app.route("/search", methods=['GET', 'POST'])
def search():
    search = get_var(request, "search")
    search_query = get_var(request, "query")
    app.logger.debug("query=%s" % search_query)
    if search == "true" and query:
        q = query(search_query)
        app.logger.debug("query=%s" % q)
        result = INDEX_DOC.search(q)
        app.logger.debug("scroll=%s" % result.scroll_id)
        return render_template("search.html",
                               query=search_query,
                               result=result,
                               sentence_index=INDEX_SEN)
    return render_template("search.html")


@app.route("/docs", methods=['GET', 'POST'])
def docs():
    result = INDEX_DOC.get_documents()
    return render_template('docs.html', sources=result.sources)


@app.route("/doc", methods=['GET', 'POST'])
def doc():
    sentid = get_var(request, "sentid")
    show_text = get_var(request, "show_text")
    docid = sentid.split('-')[0]
    doc = INDEX_DOC.get(docid)
    source = Source(None, doc['_source'])
    return render_template('doc.html', docid=docid, source=source,
                           show_text=show_text)
    return "%s\n<pre>%s</pre>" % (docid, pformat(doc))


@app.route("/help", methods=['GET'])
def help():
    return render_template('help.html')
