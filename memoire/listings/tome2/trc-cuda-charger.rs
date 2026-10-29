            unsafe fn charger() -> Result<Api, String> {
                let nom_dll: Vec<u16> = "nvcuda.dll\0".encode_utf16().collect();
                // SAFETY : chaîne terminée par un zéro ; recherche limitée à System32, où le
                // pilote d'affichage installe nvcuda.dll (pas de DLL plantée dans le dossier courant).
                let module = unsafe {
                    LoadLibraryExW(nom_dll.as_ptr(), std::ptr::null_mut(), LOAD_LIBRARY_SEARCH_SYSTEM32)
                };
                if module.is_null() {
                    return Err("nvcuda.dll introuvable dans System32 : aucun pilote NVIDIA \
                                installé, ou pilote trop ancien".into());
                }
                let symbole = |nom: &str| -> Result<unsafe extern "system" fn() -> isize, String> {
                    let c = format!("{nom}\0");
                    // SAFETY : module valide, nom terminé par un zéro.
                    unsafe { GetProcAddress(module, c.as_ptr()) }
                        .ok_or_else(|| format!("symbole {nom} absent de nvcuda.dll (pilote trop ancien ?)"))
                };
