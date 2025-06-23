-- Ensure the schema exists
CREATE SCHEMA IF NOT EXISTS ads;

-- Ensure the sequence exists
CREATE SEQUENCE IF NOT EXISTS ads.ads_id_seq;

-- Create the table
CREATE TABLE IF NOT EXISTS ads.ads
(
    id integer NOT NULL DEFAULT nextval('ads.ads_id_seq'::regclass),
    title text NOT NULL,
    description text NOT NULL,
    link text NOT NULL,
    image_url text,
    category text,
    phone text[] NOT NULL,
    date date NOT NULL,
    price text,
    currency text,
    location text NOT NULL,
    store text NOT NULL,
    CONSTRAINT ads_pkey PRIMARY KEY (id),
    CONSTRAINT ads_link_key UNIQUE (link),
    CONSTRAINT ads_phone_check CHECK (cardinality(phone) > 0)
);

-- Set table owner (optional, usually not needed)
ALTER TABLE IF EXISTS ads.ads OWNER TO postgres;
