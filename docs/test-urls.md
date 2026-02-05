| Input Kind                   | Input description                                         | Expected Kind                               | URL                                                                               |
| ---------------------------- | --------------------------------------------------------- | ------------------------------------------- | --------------------------------------------------------------------------------- |
| Album-formatted<br /> (OLAK) | Top songs playlist (Album-formatted URL)                  | Playlist                                    | https://music.youtube.com/playlist?list=OLAK5uy_meFrWp55M2SJ6yzAtKBPF1Uq_viHSihmE |
| Playlist                     | 1 ATV, 1 OMV, 1 UGC (non-music)                           | Playlist                                    | https://music.youtube.com/playlist?list=PLbE6wFkAlDUer3k6jGlQtV-4Sn5g-XhDv        |
| Playlist                     | 1 ATV                                                     | Playlist                                    | https://music.youtube.com/playlist?list=PLbE6wFkAlDUfy14yaVjdfGv4wDGmbebH4        |
| Playlist                     | 1 OMV                                                     | Playlist                                    | https://music.youtube.com/playlist?list=PLbE6wFkAlDUch0Yr7K_y_9_p5HWPC1uzg        |
| Playlist                     | 2 ATV. Same album                                         | Playlist                                    | https://music.youtube.com/playlist?list=PLbE6wFkAlDUeTMUZp1NAaD-Zw_yEBR_G_        |
| Playlist                     | Full album (SABLE, fABLE)                                 | Playlist                                    | https://music.youtube.com/playlist?list=PLbE6wFkAlDUfNsy9oWwd2UBYvAEtX74La        |
| Album (OLAK)                 | SABLE, fABLE                                              | Album                                       | https://music.youtube.com/playlist?list=OLAK5uy_mxPcDF6PkoNTfDzi7SI69_U5BtA2VYqYM |
| Playlist                     | Full album (SABLE, fABLE) + 1 random UGC (music)          | Playlist                                    | https://music.youtube.com/playlist?list=PLxA687tYuMWjZfT1YGgX6xL0PYSMCpBIb        |
| Album-formatted (OLAK)       | Top Charts Playlist. Mixed content. (Album-formatted URL) | Playlist                                    | https://music.youtube.com/playlist?list=OLAK5uy_mzYnlaHgFOvLaxqIPnnouEr-idiUn4NIM |
| Single                       | OMV                                                       | Track                                       | https://music.youtube.com/watch?v=GkTWxDB21cA                                     |
| Single                       | ATV                                                       | Track                                       | https://music.youtube.com/watch?v=Vgpv5PtWsn4                                     |
| Single                       | UGC (non-music)                                           | Skip                                        | https://www.youtube.com/watch?v=jNQXAC9IVRw                                       |
| Single                       | OMV                                                       | Skip (does not have a matching ATV version) | https://music.youtube.com/watch?v=Lw2J5rZ8kvM                                     |

Expected kind means:

- If `Playlist`: `m3u` and cover image files generated in `Playlists` folder.
- If `Album`: No additional files generated
- Web UI is correctly informed that the input URL playlist is of kind `Expected Kind` value.
