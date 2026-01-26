-- Add AI Scoring Columns to Deals Table
-- Run this to enable color-coded deal management

ALTER TABLE deals ADD COLUMN IF NOT EXISTS color VARCHAR(20) DEFAULT 'YELLOW';
ALTER TABLE deals ADD COLUMN IF NOT EXISTS assignment_fee FLOAT DEFAULT 10000;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS scored_at TIMESTAMP;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS urgency_score FLOAT;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS location_demand FLOAT;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS arv_estimate FLOAT;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS repair_estimate FLOAT;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS discount_percent FLOAT;

-- Create index for faster filtering by color
CREATE INDEX IF NOT EXISTS idx_deals_color ON deals(color);
CREATE INDEX IF NOT EXISTS idx_deals_assignment_fee ON deals(assignment_fee DESC);

-- Add comment
COMMENT ON COLUMN deals.color IS 'Deal quality: GREEN ($15K+ fee), YELLOW ($7.5K-15K fee), RED (<$7.5K fee)';
COMMENT ON COLUMN deals.assignment_fee IS 'Estimated wholesale assignment fee in USD';
