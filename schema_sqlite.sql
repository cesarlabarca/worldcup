create table if not exists teams(
  id integer primary key autoincrement,
  name text not null,
  group_name text ,
  flag_url text 
);

create table if not exists matches(
  id integer primary key autoincrement,
  home_team_id int references teams (id),
  away_team_id int references teams (id),
  home_placeholder text,
  away_placeholder text,
  stage text,
  group_name text,
  match_number int not null,
  kickoff_at datetime not null,
  home_score int,
  away_score int,
  is_locked int default 0,
  is_confirmed int default 0
);

create table if not exists users(
  id integer primary key autoincrement,
  username text not null,
  password_hash text not null,
  is_admin int default 0,
  created_at datetime default (datetime('now'))
);

create table if not exists predictions(
  id integer primary key autoincrement,
  user_id int references users (id),
  match_id int references matches (id),
  home_score int not null,
  away_score int not null,
  points_earned int,
  submitted_at datetime default (datetime('now'))
);



