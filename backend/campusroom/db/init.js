import 'dotenv/config'; import pg from 'pg'; import bcrypt from 'bcryptjs'; import { readFile } from 'node:fs/promises';
const db = new pg.Pool({ connectionString: process.env.DATABASE_URL });
const sql = await readFile(new URL('./schema.sql', import.meta.url), 'utf8'); await db.query(sql);
await db.query('ALTER TABLE meetings ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()');
const users=[['Aarav Student','student@campusroom.edu','student','Computer Science'],['Dr. Maya Rao','faculty@campusroom.edu','faculty','Computer Science'],['Student Welfare Office','welfare@campusroom.edu','welfare','Administration'],['Campus Director','director@campusroom.edu','director','Administration'],['Events Office','events@campusroom.edu','events','Events']];
const hash=await bcrypt.hash('Campus@123',12); for(const [name,email,role,department] of users) await db.query('INSERT INTO users(name,email,password_hash,role,department) VALUES($1,$2,$3,$4,$5) ON CONFLICT(email) DO NOTHING',[name,email,hash,role,department]);
const halls=[['New Auditorium / Pandal',3000],['Amriteswari Hall',520],['Sudhamani Hall',500],['Seminar Hall I',200],['Seminar Hall II',200],['Achariya Hall (AB I)',130],['Sandeepani Hall (AB II)',225],['Anugraha Hall (AB III)',185],['Vivekha Hall (AB I)',23],['Saraswathy Hall',23],['Event Hall',180]]; for(const [name,capacity] of halls) await db.query('INSERT INTO halls(name,capacity) VALUES($1,$2) ON CONFLICT(name) DO NOTHING',[name,capacity]);
await db.end(); console.log('CampusRoom database ready.');
