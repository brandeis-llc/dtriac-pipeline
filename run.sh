#! /bin/bash 

# prepare tools
spv1_container=$(docker ps --format '{{.Image}}\t{{.Names}}\t{{.Ports}}' | grep -E ^allenai\/scienceparse:2.0.3)
corenlp_jar=$(pwd)/brandeis-stanfordnlp-service/corenlp-cli#2.2.0-jar-with-dependencies.jar
reverb_jar=$(pwd)/brandeis-reverb-service/reverb-cli#1.1.0-jar-with-dependencies.jar
clearwsd_jar=$(pwd)/clearwsd/clearwsd-cli-0.10-SNAPSHOT.jar
clearwsd_model=$(pwd)/clearwsd/clearwsd-models/src/main/resources/models/nlp4j-verbnet-3.3.bin

## science-parser (v1) as a container
if [ -n "$spv1_container" ]; then 
    spv1_container_name=$(echo "$spv1_container" | cut -f 2)
    spv1_container_port=$(echo "$spv1_container" | cut -f 3  | cut -d - -f 1 | cut -d : -f 2)
else
    spv1_container_name="spv1"
    spv1_container_port="8123"
    docker run -d -p ${spv1_container_port}:8080 --rm --name ${spv1_container_name} allenai/scienceparse:2.0.3
    spv1_running=$(curl -I localhost:${spv1_container_port} 2>/dev/null | head -n 1 | cut -d$' ' -f2)
    until [ "$spv1_running" = "405" ] ; do 
        spv1_running=$(curl -I localhost:${spv1_container_port} 2>/dev/null | head -n 1 | cut -d$' ' -f2)
    done
fi
## corenlp (Brandeis lapps version)
if [ ! -f ${corenlp_jar} ]; then 
    rm -rf $(pwd)/brandeis-stanfordnlp-service
    git clone --branch v2.2.0 https://github.com/lappsgrid-services/brandeis-stanfordnlp-service.git
    cd brandeis-stanfordnlp-service
    mvn -DskipTests -Pcli package &
    cd ..
fi
### example cmd: jar corenlp-cli#2.2.0-SNAPSHOT-jar-with-dependencies.jar ner /home/krim/Projects/dtra-534/spv1-results-lif
### will create a subdir "ner-TIMESTAMP" in the input dir
### and generated NER lifs share the same names with input file
## reverb (Brandeis lapps version)
if [ ! -f ${reverb_jar} ]; then 
    rm -rf $(pwd)/brandeis-reverb-service
    git clone --branch v1.1.0 https://github.com/lappsgrid-services/brandeis-reverb-service.git
    cd brandeis-reverb-service
    mvn -DskipTests -Pcli package &
    cd ..
fi
## clearwsd (Keigh's fork)
if [ ! -f ${clearwsd_jar} ]; then 
    rm -rf $(pwd)/clearwsd
    git clone --branch develop https://github.com/keighrim/clearwsd.git
    cd clearwsd
    mvn package -DskipTests -P build-nlp4j-cli & 
    cd ..
fi 
### example command: java -jar clearwsd-cli-0.10-SNAPSHOT.jar -model clearwsd-models/src/main/resources/models/nlp4j-verbnet-3.3.bin  -input "$f" -output "output/$(basename "$f")" --anchor
## technology extraction
## Tarsqi 

# wait for all jobs are done 
wait

pdf_loc=$1
out_loc=$2
spv1_jsons="$2/1-spv1-results"
raw_lifs="$2/2-1-raw-lif"
raw_texts="$2/2-2-raw-text"
ner_lifs="$2/3-ner"
# 4. as well as technology extraction 
tex_lifs="$2/4-tex"
# 5. next tarsqi
tarsqi_lifs="$2/5-ttk"
# 6. and crap sentence classification 
sentence_cls="$2/6-sen"
# 7. reverb
reverb_lifs="$2/7-rel"
# 8. and clearwsd
verbnet_tags="$2/8-vnc"
# 9. and finally gensim 
topic_models="$2/9-top"
elastic_jsons="$2/es-index"

for dir in {$spv1_jsons,$raw_lifs,$raw_texts,$ner_lifs,$tex_lifs,$tarsqi_lifs,$sentence_cls,$reverb_lifs,$verbnet_tags,$topic_models,$elastic_jsons}; do 
    if [ ! -d ${dir} ] ; then 
        mkdir -p ${dir}
    fi
done

echo $spv1_container_port

# 1. first extract text and basic metadata using spv1
for pdf in "$pdf_loc"/*.pdf; do 
    curl -v -H "Content-type: application/pdf" --data-binary @"${pdf}" http://localhost:${spv1_container_port}/v1 > ${spv1_jsons}/"$(basename ${pdf})".json
done
# 2. then convert spv1 json to LIF

for json in ${spv1_jsons}/*.json ; do 
    python $(pwd)/scripts/create_lif.py ${spv1_jsons} ${raw_lifs} ${raw_texts}
done

# 3. now run corenlp NER
rm -rf ${raw_lifs}/ner-*
java -jar ${corenlp_jar} ner ${raw_lifs} && mv ${raw_lifs}/ner-*/*.lif ${ner_lifs} && rm -rf ${raw_lifs}/ner-* &
# 4. as well as technology extraction 
# 5. next tarsqi
# 6. and crap sentence classification 
# 7. reverb
rm -rf ${raw_lifs}/rel-*
java -jar ${reverb_jar} ${raw_lifs} && mv ${raw_lifs}/rel-*/*.lif ${reverb_lifs} && rm -rf ${raw_lifs}/rel-* &
# 8. and clearwsd
rm -rf ${raw_texts}/clearwsd
mkdir -p ${raw_texts}/clearwsd
for t in ${raw_texts}/*.txt; do 
    txt=$(basename $t)
    (java -jar ${clearwsd_jar} -model ${clearwsd_model}  -input "${raw_texts}/$txt" -output "${raw_texts}/clearwsd/$txt" --anchor 
    python ./scripts/vnc_to_lif.py "${raw_texts}/$txt" "${raw_texts}/clearwsd/$txt" > "${verbnet_tags}/$txt".lif 
    rm ${raw_texts}/clearwsd/${txt}
    rm ${raw_texts}/${txt}.dep
    ) &
done
# 9. and finally gensim 


wait
docker stop ${spv1_container_name} && docker rm ${spv1_container_name}
