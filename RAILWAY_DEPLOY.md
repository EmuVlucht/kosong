# Deploy M-Mail ke Railway

Panduan lengkap untuk deploy aplikasi M-Mail ke Railway.

## Langkah 1: Siapkan Repository

1. Push kode ke GitHub repository kamu
2. Pastikan semua file sudah ter-commit

## Langkah 2: Buat Project di Railway

1. Buka [Railway](https://railway.app) dan login
2. Klik **New Project**
3. Pilih **Deploy from GitHub repo**
4. Pilih repository M-Mail kamu

## Langkah 3: Tambah Database PostgreSQL

1. Di project Railway, klik **+ New**
2. Pilih **Database** > **Add PostgreSQL**
3. Tunggu database selesai dibuat
4. Klik database PostgreSQL yang baru dibuat
5. Buka tab **Variables**
6. Salin nilai `DATABASE_URL`

## Langkah 4: Set Environment Variables

Di service aplikasi (bukan database), buka tab **Variables** dan tambahkan:

| Variable | Nilai | Keterangan |
|----------|-------|------------|
| `AUTH_DATABASE_URL` | (paste dari database) | URL koneksi PostgreSQL |
| `GOOGLE_CLIENT_ID` | (dari Google Cloud Console) | Client ID Google OAuth |
| `GOOGLE_CLIENT_SECRET` | (dari Google Cloud Console) | Client Secret Google OAuth |
| `SECRET_KEY` | (generate random string) | Secret key untuk session |
| `FLASK_ENV` | `production` | Mode production |

## Langkah 5: Konfigurasi Google OAuth

1. Buka [Google Cloud Console](https://console.cloud.google.com)
2. Pilih project yang memiliki OAuth credentials
3. Buka **APIs & Services** > **Credentials**
4. Klik OAuth 2.0 Client ID yang digunakan
5. Di bagian **Authorized redirect URIs**, tambahkan:
   ```
   https://YOUR-APP-NAME.up.railway.app/auth/callback
   ```
   Ganti `YOUR-APP-NAME` dengan nama app Railway kamu

## Langkah 6: Deploy

1. Railway akan otomatis build dan deploy
2. Tunggu sampai status menjadi **Active**
3. Klik **Generate Domain** untuk mendapatkan URL publik

## Langkah 7: Verifikasi

1. Buka URL aplikasi Railway
2. Klik tombol **Login dengan Google**
3. Pastikan login berhasil
4. Buat email sementara dan verifikasi tersimpan di akun

## Troubleshooting

### Error: Database connection failed
- Pastikan `AUTH_DATABASE_URL` sudah diset dengan benar
- Cek format URL: harus dimulai dengan `postgresql://` atau `postgres://`

### Error: OAuth redirect mismatch
- Pastikan redirect URI di Google Console sama persis dengan URL Railway
- Jangan lupa sertakan `/auth/callback` di akhir URL

### Error: Application not starting
- Cek logs di Railway untuk melihat error
- Pastikan semua environment variables sudah diset

## Environment Variables yang Dibutuhkan

| Variable | Wajib | Deskripsi |
|----------|-------|-----------|
| `AUTH_DATABASE_URL` | Ya | URL PostgreSQL |
| `GOOGLE_CLIENT_ID` | Ya | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Ya | Google OAuth Client Secret |
| `SECRET_KEY` | Disarankan | Random string untuk session |
| `FLASK_ENV` | Opsional | Set ke `production` |

## Catatan Penting

- Database akan otomatis membuat tabel saat aplikasi pertama kali dijalankan
- Semua email sementara akan tersimpan di database PostgreSQL
- Backup database secara berkala untuk menghindari kehilangan data
