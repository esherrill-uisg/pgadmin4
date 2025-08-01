-- Index: Idx1_$%{}[]()&*^!@"'`\/#

-- DROP INDEX IF EXISTS public."Idx1_$%{}[]()&*^!@""'`\/#";

CREATE UNIQUE INDEX IF NOT EXISTS "Idx1_$%{}[]()&*^!@""'`\/#"
    ON public.test_table_for_indexes USING btree
    (id DESC NULLS FIRST, name COLLATE pg_catalog."POSIX" text_pattern_ops DESC NULLS FIRST)
    INCLUDE(name, id)
    NULLS NOT DISTINCT
    WITH (fillfactor=10, deduplicate_items=True)
    TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.test_table_for_indexes
    CLUSTER ON "Idx1_$%{}[]()&*^!@""'`\/#";

COMMENT ON INDEX public."Idx1_$%{}[]()&*^!@""'`\/#"
    IS 'Test Comment';
