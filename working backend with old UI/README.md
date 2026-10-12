# BOOkIT

A role-secure campus event proposal, approval and booking portal.

## Run

```bash
cp .env.example .env
docker compose up -d
npm install
npm run db:init
npm run dev
```

Open http://localhost:3000. Seeded passwords are `Campus@123`.

| Role | Email |
|---|---|
| Student | student@campusroom.edu |
| Faculty | faculty@campusroom.edu |
| Student Welfare | welfare@campusroom.edu |
| Campus Director | director@campusroom.edu |
| Events Office | events@campusroom.edu |

The schema is PostgreSQL. `db/init.js` is idempotent and creates halls, users and tables. File uploads are deliberately stored locally in `uploads/` for development; use object storage and virus scanning before production.
