## Test URLs

| Kind  | Description                       | URL                                                                               |
| ----- | --------------------------------- | --------------------------------------------------------------------------------- |
| OLAK  | Top songs playlist                | https://music.youtube.com/playlist?list=OLAK5uy_meFrWp55M2SJ6yzAtKBPF1Uq_viHSihmE |
| PL    | 1 ATV, 1 OMV, 1 UGC (non-music)   | https://music.youtube.com/playlist?list=PLbE6wFkAlDUer3k6jGlQtV-4Sn5g-XhDv        |
| PL    | 1 ATV                             | https://music.youtube.com/playlist?list=PLbE6wFkAlDUfy14yaVjdfGv4wDGmbebH4        |
| PL    | 1 OMV                             | https://music.youtube.com/playlist?list=PLbE6wFkAlDUch0Yr7K_y_9_p5HWPC1uzg        |
| PL    | 2 ATV. Same album                 | https://music.youtube.com/playlist?list=PLbE6wFkAlDUeTMUZp1NAaD-Zw_yEBR_G_        |
| PL    | Full album (SABLE, fABLE)         | https://music.youtube.com/playlist?list=PLbE6wFkAlDUfNsy9oWwd2UBYvAEtX74La        |
| OLAK  | Album (SABLE, fABLE)              | https://music.youtube.com/playlist?list=OLAK5uy_mxPcDF6PkoNTfDzi7SI69_U5BtA2VYqYM |
| PL    | Full album (SABLE, fABLE) + 1 UGC | https://music.youtube.com/playlist?list=PLxA687tYuMWjZfT1YGgX6xL0PYSMCpBIb        |
| OLAK  | Top Charts Playlist               | https://music.youtube.com/playlist?list=OLAK5uy_mzYnlaHgFOvLaxqIPnnouEr-idiUn4NIM |
| Video | OMV                               | https://music.youtube.com/watch?v=GkTWxDB21cA                                     |
| Video | ATV                               | https://music.youtube.com/watch?v=Vgpv5PtWsn4                                     |
| Video | UGC                               | https://www.youtube.com/watch?v=jNQXAC9IVRw                                       |
| Video | OMV                               | https://music.youtube.com/watch?v=Lw2J5rZ8kvM                                     |
| Video | OMV (no ATV match)                | https://www.youtube.com/watch?v=-HJ0ZGkdlTk                                       |
| Video | OFFICIAL_SOURCE_MUSIC             | https://music.youtube.com/watch?v=FPYgJks1Zy0                                     |
| Video | OFFICIAL_SOURCE_MUSIC             | https://music.youtube.com/watch?v=k3UevKvP9RU                                     |
| PL    | 1 OFFICIAL_SOURCE_MUSIC           | https://music.youtube.com/playlist?list=PLbE6wFkAlDUf_oicZwbgEAEmBfKIy43Rf        |

## Supported URLs

| Domain           | Downloaded content | URL path            | Example URL                                                                           |
| ---------------- | ------------------ | ------------------- | ------------------------------------------------------------------------------------- |
| (\*.)youtube.com | Album/Playlist     | /playlist           | https://music.youtube.com/playlist?list=OLAK5uy_m0Ye5titJYUtPwc3RZUwl5iXJ60NUJLEg     |
| (\*.)youtube.com | Album/Playlist     | /watch?v={}&list={} | https://music.youtube.com/watch?v=Tdv8XKco7PY&list=PLbE6wFkAlDUer3k6jGlQtV-4Sn5g-XhDv |
| (\*.)youtube.com | Track              | /watch?v={}         | https://youtube.com/watch?v=psG9hPSkqJg                                               |
| (\*.)youtube.com | N/A                | /                   | https://www.youtube.com/                                                              |
| (\*.)youtube.com | N/A                | /channel/{}         | https://www.youtube.com/channel/UCfIXdjDQH9Fau7y99_Orpjw                              |

Anything that is not `/playlist` or `/watch`, N/A.
