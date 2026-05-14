CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    group_name TEXT,
    flag_url TEXT
);

CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    home_placeholder TEXT,
    away_placeholder TEXT,
    stage TEXT,
    group_name TEXT,
    match_number INTEGER NOT NULL,
    kickoff_at TIMESTAMP NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    is_locked INTEGER DEFAULT 0,
    is_confirmed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    match_id INTEGER REFERENCES matches(id),
    home_score INTEGER NOT NULL,
    away_score INTEGER NOT NULL,
    points_earned INTEGER,
    submitted_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, match_id)
);