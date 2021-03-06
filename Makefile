SHELL = /bin/bash

sh:
	docker-compose run --rm bigmetadata /bin/bash

extension-perftest: extension
	docker-compose run --rm bigmetadata nosetests -s observatory-extension/src/python/test/perftest.py

extension-perftest-record: extension
	mkdir -p perftest
	docker-compose run --rm \
	  -e OBS_RECORD_TEST=true \
	  -e OBS_PERFTEST_DIR=perftest \
	  -e OBS_EXTENSION_SHA=$$(cd observatory-extension && git rev-list -n 1 HEAD) \
	  -e OBS_EXTENSION_MSG="$$(cd observatory-extension && git rev-list --pretty=oneline -n 1 HEAD)" \
	  bigmetadata \
	  nosetests observatory-extension/src/python/test/perftest.py

extension-autotest: extension
	docker-compose run --rm bigmetadata nosetests observatory-extension/src/python/test/autotest.py

test: extension-perftest extension-autotest

python:
	docker-compose run --rm bigmetadata python

build:
	docker build -t carto/bigmetadata:latest .

build-postgres:
	docker build -t carto/bigmetadata_postgres:latest postgres

psql:
	docker-compose run --rm bigmetadata psql

clean-catalog:
	sudo rm -rf catalog/source/*/*
	# Below code eliminates everything not removed by the command above.
	# The trick here is that catalog/source is mostly ignored, but
	# we don't want to delete catalog/source/conf.py and
	# catalog/source/index.rst
	sudo git status --porcelain --ignored -- catalog/source/* \
	  | grep '^!!' \
	  | cut -c 4-1000 \
	  | xargs rm -f

catalog: clean-catalog
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.sphinx Catalog \
	  $${SECTION/#/--section } \
	  --local-scheduler
	docker-compose up -d nginx
	echo Catalog accessible at http://$$(curl -s 'https://api.ipify.org')$$(docker-compose ps | grep nginx | grep -oE ':[0-9]+')/catalog/

pdf-catalog:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.sphinx Catalog --format pdf

md-catalog:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.sphinx Catalog --format markdown \
	  --local-scheduler

deploy-pdf-catalog:
	docker-compose run --rm bigmetadata luigi \
	    --module tasks.sphinx PDFCatalogToS3

deploy-html-catalog:
	cd catalog/build/html && \
	sudo chown -R ubuntu:ubuntu . && \
	touch .nojekyll && \
	git init && \
	git checkout -B gh-pages && \
	git add . && \
	git commit -m "updating catalog" && \
	(git remote add origin git@github.com:cartodb/bigmetadata.git || : ) && \
	git push -f origin gh-pages

deploy-md-catalog:
	cd catalog/build/markdown && \
	sudo chown -R ubuntu:ubuntu . && \
	touch .nojekyll && \
	git init && \
	git checkout -B markdown-catalog && \
	git add . && \
	git commit -m "updating catalog" && \
	(git remote add origin git@github.com:cartodb/bigmetadata.git || : ) && \
	git push -f origin markdown-catalog

deploy-catalog: deploy-pdf-catalog deploy-html-catalog deploy-md-catalog

# do not exceed three slots available for import api
sync: sync-data sync-meta

sync-data:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.carto SyncAllData \
	  --parallel-scheduling --workers=3

sync-meta:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.carto SyncMetadata \
	  --parallel-scheduling --workers=3

kill:
	docker-compose ps | grep _run_ | cut -c 1-34 | xargs docker stop

# http://stackoverflow.com/questions/2214575/passing-arguments-to-make-run#2214593
ifeq (run,$(firstword $(MAKECMDGOALS)))
  # use the rest as arguments for "run"
  RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  # ...and turn them into do-nothing targets
  $(eval $(RUN_ARGS):;@:)
endif

ifeq (run-parallel,$(firstword $(MAKECMDGOALS)))
  # use the rest as arguments for "run"
  RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  # ...and turn them into do-nothing targets
  $(eval $(RUN_ARGS):;@:)
endif

ifeq (deps-tree,$(firstword $(MAKECMDGOALS)))
  # use the rest as arguments for "run"
  RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  # ...and turn them into do-nothing targets
  $(eval $(RUN_ARGS):;@:)
endif

.PHONY: run run-parallel catalog docs carto restore dataservices-api

run:
	docker-compose run --rm bigmetadata luigi --local-scheduler --module tasks.$(RUN_ARGS)

run-parallel:
	docker-compose run --rm bigmetadata luigi --parallel-scheduling --workers=8 --module tasks.$(RUN_ARGS)

dump: test
	docker-compose run --rm bigmetadata luigi --module tasks.carto DumpS3

# update the observatory-extension in our DB container
# Depends on having an observatory-extension folder linked
extension:
	docker exec $$(docker-compose ps -q postgres) sh -c 'cd observatory-extension && make install'
	docker-compose run --rm bigmetadata psql -c "DROP EXTENSION IF EXISTS observatory; CREATE EXTENSION observatory WITH VERSION 'dev';"

# update dataservices-api in our DB container
# Depends on having a dataservices-api folder linked
dataservices-api: extension
	docker exec $$(docker-compose ps -q postgres) sh -c ' \
	  cd /cartodb-postgresql && make install && \
	  cd /data-services/geocoder/extension && make install && \
	  cd /dataservices-api/client && make install && \
	  cd /dataservices-api/server/extension && make install && \
	  cd /dataservices-api/server/lib/python/cartodb_services && \
	  pip install -r requirements.txt && pip install --upgrade .'
	docker-compose run --rm bigmetadata psql -f /bigmetadata/postgres/dataservices_config.sql
	docker exec $$(docker-compose ps -q redis) sh -c \
	  "$$(cat postgres/dataservices_config.redis)"

## in redis:


sh-sql:
	docker exec -it $$(docker-compose ps -q postgres) /bin/bash

py-sql:
	docker exec -it $$(docker-compose ps -q postgres) python

# Regenerate fixtures for the extension
extension-fixtures:
	docker-compose run --rm bigmetadata \
	  python observatory-extension/scripts/generate_fixtures.py

extension-unittest:
	docker exec -it \
	  $$(docker-compose ps -q postgres) \
	  /bin/bash -c "cd observatory-extension \
	                && chmod -R a+w src/pg/test/results \
	                && make install \
	                && su postgres -c 'make test'"

dataservices-api-client-unittest:
	docker exec -it \
	  $$(docker-compose ps -q postgres) \
	  /bin/bash -c "cd dataservices-api/client \
	                && chmod -R a+w test \
	                && make install \
	                && su postgres -c 'PGUSER=postgres make installcheck'" || :
	test $$(grep '^[-+] ' dataservices-api/client/test/regression.diffs | grep -Ev '(CONTEXT|PL/pgSQL)' | tee dataservices-api/client/test/regression.diffs | wc -l) = 0

dataservices-api-server-unittest:
	docker exec -it \
	  $$(docker-compose ps -q postgres) \
	  /bin/bash -c "cd dataservices-api/server/extension \
	                && chmod -R a+w test \
	                && make install \
	                && su postgres -c 'PGUSER=postgres make installcheck'" || :

dataservices-api-unittest: dataservices-api-server-unittest dataservices-api-client-unittest

etl-unittest:
	docker-compose run --rm bigmetadata /bin/bash -c \
	  'while : ; do pg_isready -t 1 && break; done && \
	  PGDATABASE=test nosetests -v \
	    tests/test_meta.py tests/test_util.py tests/test_carto.py \
	    tests/test_tabletasks.py'

etl-metadatatest:
	docker-compose run --rm bigmetadata /bin/bash -c \
	  'while : ; do pg_isready -t 1 && break; done && \
	  TEST_ALL=$(ALL) TEST_MODULE=tasks.$(MODULE) \
	  PGDATABASE=test nosetests -v --with-timer \
	    tests/test_metadata.py'

travis-etl-unittest:
	./run-travis.sh \
	  'nosetests -v \
	    tests/test_meta.py tests/test_util.py tests/test_carto.py \
	    tests/test_tabletasks.py'

travis-diff-catalog:
	git fetch origin master
	./run-travis.sh 'python -c "from tests.util import recreate_db; recreate_db()"'
	./run-travis.sh 'ENVIRONMENT=test luigi --local-scheduler --module tasks.util RunDiff --compare FETCH_HEAD'
	./run-travis.sh 'ENVIRONMENT=test luigi --local-scheduler --module tasks.sphinx Catalog --force'

travis-etl-metadatatest:
	./run-travis.sh 'nosetests -v tests/test_metadata.py'

restore:
	docker-compose run --rm -d bigmetadata pg_restore -U docker -j4 -O -x -e -d gis $(RUN_ARGS)

docs:
	docker-compose run --rm bigmetadata /bin/bash -c 'cd docs && make html'

tiles:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.util GenerateAllRasterTiles \
	  --parallel-scheduling --workers=5

ps:
	docker-compose ps

stop:
	docker-compose stop

up:
	docker-compose up -d

meta:
	docker-compose run --rm bigmetadata luigi\
	  --module tasks.carto OBSMetaToLocal --force

releasetest: extension-fixtures extension-perftest-record extension-unittest extension-autotest

test-catalog:
	docker-compose run --rm bigmetadata /bin/bash -c \
	  'while : ; do pg_isready -t 1 && break; done && \
	  TEST_MODULE=tasks.$(MODULE) PGDATABASE=test nosetests -vs \
	    tests/test_catalog.py'

diff-catalog: clean-catalog
	git fetch origin master
	docker-compose run -e PGDATABASE=test -e ENVIRONMENT=test --rm bigmetadata /bin/bash -c \
	  'python -c "from tests.util import recreate_db; recreate_db()" && \
	   luigi --local-scheduler --retcode-task-failed 1 --module tasks.util RunDiff --compare FETCH_HEAD && \
	   luigi --local-scheduler --retcode-task-failed 1 --module tasks.sphinx Catalog'

deps-tree:
	docker-compose run --rm bigmetadata luigi-deps-tree --module tasks.$(RUN_ARGS)

###### Import tasks

### au
au-all:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.au.data BCPAllGeographiesAllTables --year 2011 \
	  --parallel-scheduling --workers=8

au-geo:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.au.geo AllGeographies --year 2011 \
	  --parallel-scheduling --workers=8

### br
br-all: br-geo br-census

br-census:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.br.data CensosAllGeographiesAllTables \
		--parallel-scheduling --workers=8

br-geo:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.br.geo AllGeographies \
		--parallel-scheduling --workers=8

### ca
ca-all: ca-nhs-all ca-census-all

ca-nhs-all:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.ca.statcan.data AllNHSTopics \
		--parallel-scheduling --workers=8

ca-census-all:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.ca.statcan.data AllCensusTopics \
		--parallel-scheduling --workers=8

ca-geo:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.ca.statcan.geo AllGeographies \
		--parallel-scheduling --workers=8

### es
es-all: es-cnig es-ine

es-cnig:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.es.cnig AllGeometries \
		--parallel-scheduling --workers=8

es-ine: es-ine-phh es-ine-fyp

es-ine-phh:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.es.ine PopulationHouseholdsHousingMeta \
		--parallel-scheduling --workers=8

es-ine-fyp:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.es.ine FiveYearPopulationMeta \
		--parallel-scheduling --workers=8

### eurostat
eu-all: eu-geo eu-data

eu-geo:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.eu.geo NUTSGeometries \
	  --parallel-scheduling --workers=8

eu-data:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.eu.eurostat EURegionalTables \
	  --parallel-scheduling --workers=8

### fr
fr-all:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.fr.insee InseeAll \
		--parallel-scheduling --workers=8

### mx
mx-all: mx-geo mx-census

mx-geo:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.mx.inegi AllGeographies \
		--parallel-scheduling --workers=8

mx-census:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.mx.inegi AllCensus \
		--parallel-scheduling --workers=8

### us
us-all: us-bls us-acs us-lodes us-spielman us-tiger us-enviroatlas us-huc us-dcp us-dob us-zillow

us-bls:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.us.bls AllQCEW \
		--parallel-scheduling --workers=8

us-acs:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.us.census.acs ACSAll \
		--parallel-scheduling --workers=8

us-lodes:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.us.census.lodes LODESMetaWrapper --geography block --year 2013 \
		--parallel-scheduling --workers=8

us-spielman:
	docker-compose run --rm bigmetadata luigi \
		--module tasks.us.census.spielman_singleton_segments SpielmanSingletonMetaWrapper \
		--parallel-scheduling --workers=8

us-tiger:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.us.census.tiger AllSumLevels --year 2015 \
	  --parallel-scheduling --workers=8

us-enviroatlas:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.us.epa.enviroatlas AllTables \
	  --parallel-scheduling --workers=8

us-huc:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.us.epa.huc HUC \
	  --parallel-scheduling --workers=8

us-dcp:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.us.ny.nyc.dcp MapPLUTOAll \
	  --parallel-scheduling --workers=8

us-dob:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.us.ny.nyc.dob PermitIssuance \
	  --parallel-scheduling --workers=8

us-zillow:
	docker-compose run --rm bigmetadata luigi \
	  --module tasks.us.zillow AllZillow \
	  --parallel-scheduling --workers=8
