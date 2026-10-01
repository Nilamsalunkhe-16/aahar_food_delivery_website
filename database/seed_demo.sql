-- Run after schema.sql if you want sample dashboard data.
-- The website also has front-end fallback demo cards, so this is optional.
INSERT INTO impact_metrics(food_rescued_kg, meals_served, people_reached, organizations_helped)
VALUES
(48, 120, 35, 8),
(62, 165, 52, 11),
(84, 220, 73, 15);
