# Book-It Events Service

A role-secure campus event proposal, approval and booking portal.

## Run

```bash
copy .env.example .env
npm ci
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

The schema is PostgreSQL. `db/init.js` is idempotent and creates halls, users and tables. The repository-root `docker-compose.yml` starts this service with its database. File uploads are stored locally in `uploads/` for development; use object storage and virus scanning before production.
