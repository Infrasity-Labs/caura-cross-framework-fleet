#!/usr/bin/env bash
# Show every memory in the most recent fleet: who wrote it and whether it is still active.
docker exec caura-db-1 sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
  select agent_id, status, content from memories
  where fleet_id = (select fleet_id from memories order by created_at desc limit 1)
  order by created_at"'
