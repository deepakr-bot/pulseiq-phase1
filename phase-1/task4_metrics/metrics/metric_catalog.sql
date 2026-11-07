CREATE OR REPLACE VIEW metric_catalog AS
SELECT d.metric_id, d.metric_name, d.business_definition AS definition, d.formula,
       d.source_table AS source, d.grain, d.owner_team AS owner, d.minimum_group_size,
       v.table_name AS view_name
FROM main.metric_dictionary d
LEFT JOIN information_schema.tables v
  ON v.table_type = 'VIEW' AND v.table_schema = 'main' AND v.table_name LIKE lower(d.metric_id) || '_%'
ORDER BY d.metric_id;