from flask import Flask, render_template, request
from pprint import pformat

from utils.elastic import Index, Source
from utils.query import query
from utils.misc import get_var, Statistics, Kibana


#INDEX_DOC = Index('demo_documents_479')
INDEX_DOC = Index('demo_documents_025')

STATS_FILE = 'data/stats.json'
#STATS_FILE = 'data/stats-479.json'


app = Flask(__name__)


@app.route("/")
def index():
    stats = Statistics(STATS_FILE)
    kibana = Kibana()
    return render_template("index.html", stats=stats, kibana=kibana)


@app.route("/search", methods=['GET', 'POST'])
def search():
    kibana = Kibana()
    search = get_var(request, "search")
    search_query = get_var(request, "query")
    debug = get_var(request, "debug")
    sentences = get_var(request, "sentences")
    sentences = 5 if sentences is None else int(sentences)
    visualize = False if get_var(request, "visualize") is None else True
    app.logger.debug("query=%s" % search_query)
    if search == "true" and search_query:
        q = query(search_query)
        app.logger.debug("query=%s" % q)
        result = INDEX_DOC.search(q)
        # app.logger.debug("scroll=%s" % result.scroll_id)
        return render_template("search.html",
                               query=search_query,
                               result=result,
                               visualize=visualize,
                               kibana=kibana,
                               debug=debug,
                               sentences=sentences,
                               app=app)
    return render_template("search.html")


@app.route("/docs", methods=['GET', 'POST'])
def docs():
    result = INDEX_DOC.get_documents()
    return render_template('docs.html', sources=result.sorted_sources())


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



if __name__ == '__main__':

    app.run(host='0.0.0.0', debug=True)
