from flask import Flask, render_template, request
from pprint import pformat
import json

from utils.elastic import Index, Source
from utils.query import query
from utils.misc import get_var


INDEX_DOC = Index('demo_documents')
INDEX_SEN = Index('demo_sentences')
VERBNETCLASS_DICT = 'small-25-vncdict.json'


app = Flask(__name__)

verbnetclass_dict = None
verbnetclass_inversedict = None

@app.route("/")
def index():
    return render_template("index.html")


def read_vnc_dict(dict_filename):
    d = json.load(open(dict_filename))
    id = {}
    for verb, classes in d:
        for cls in classes:
            verbs = id.get(cls, [])
            verbs.append(verb)
            id[cls] = verbs
    return d, id


@app.route("/search", methods=['GET', 'POST'])
def search():

    global verbnetclass_dict
    global verbnetclass_inversedict
    if verbnetclass_dict is None and verbnetclass_inversedict is None:
        verbnetclass_dict, verbnetclass_inversedict = read_vnc_dict(VERBNETCLASS_DICT)
    search = get_var(request, "search")
    search_query = get_var(request, "query")
    app.logger.debug("query=%s" % search_query)
    if search == "true" and query:
        q = query(search_query, verbnetclass_dict, verbnetclass_inversedict)
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


if __name__ == '__main__':
    app.run(defug=True)
