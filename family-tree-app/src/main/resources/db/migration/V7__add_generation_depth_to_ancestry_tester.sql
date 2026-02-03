-- Add generation_depth column for storing max tree depth (capped at 8 for display)
ALTER TABLE ancestry_tester ADD COLUMN generation_depth INT;
