-- Add primary_cluster_id to ancestry_tester for MRCA display
-- A match can belong to multiple clusters via match_cluster,
-- but primary_cluster_id designates the one shown on the matches page.

ALTER TABLE ancestry_tester
ADD COLUMN primary_cluster_id INTEGER REFERENCES cluster(id);

COMMENT ON COLUMN ancestry_tester.primary_cluster_id IS
    'Primary cluster for MRCA display. Links to cluster.ahnentafel_1/2 for the common ancestor couple.';

-- Index for efficient joins on matches page
CREATE INDEX idx_ancestry_tester_primary_cluster ON ancestry_tester(primary_cluster_id);
