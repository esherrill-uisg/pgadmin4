CREATE UNIQUE INDEX "Idx_$%{}[]()&*^!@""'`\/#"
    ON public.test_table_for_indexes USING btree
    (id ASC NULLS FIRST, name COLLATE pg_catalog."POSIX" text_pattern_ops ASC NULLS FIRST)
    WITH (fillfactor=10, deduplicate_items=True)
    TABLESPACE pg_default
    WHERE id < 100;

COMMENT ON INDEX public."Idx_$%{}[]()&*^!@""'`\/#"
    IS 'Test Comment';
