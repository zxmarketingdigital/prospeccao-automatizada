CREATE TABLE IF NOT EXISTS prospects (
  id              uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  business_name   text NOT NULL,
  phone           text,
  email           text,
  website         text,
  segment         text NOT NULL,
  location        text,
  rating          real,
  score           real DEFAULT 0,
  temperature     text DEFAULT 'frio',
  potential       text DEFAULT '',
  price           text,
  contact_name    text DEFAULT '',
  source          text DEFAULT 'apify',
  current_step    integer DEFAULT 0,
  channel         text DEFAULT 'whatsapp',
  responded       boolean DEFAULT false,
  responded_at    timestamptz,
  converted       boolean DEFAULT false,
  converted_at    timestamptz,
  step1_sent_at   timestamptz,
  step2_sent_at   timestamptz,
  step3_sent_at   timestamptz,
  step4_sent_at   timestamptz,
  step5_sent_at   timestamptz,
  step6_sent_at   timestamptz,
  step7_sent_at   timestamptz,
  notes           text DEFAULT '',
  raw_data        jsonb DEFAULT '{}',
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prospects_segment ON prospects(segment);
CREATE INDEX IF NOT EXISTS idx_prospects_responded ON prospects(responded);
CREATE INDEX IF NOT EXISTS idx_prospects_score ON prospects(score DESC);
CREATE INDEX IF NOT EXISTS idx_prospects_phone ON prospects(phone);

ALTER TABLE prospects ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all" ON prospects FOR ALL
  TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "authenticated_all" ON prospects FOR ALL
  TO authenticated USING (true) WITH CHECK (true);

CREATE TRIGGER set_updated_at_prospects
  BEFORE UPDATE ON prospects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
