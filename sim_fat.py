import json
import os
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext, ttk

#Todas las configuraciones necesarias en los directorios y colores de la interfaz
TAMAÑO_BLOQUE = 20
DIR_FAT = 'fat_data'
DIR_DATOS = 'datos_archivos'
PROPIETARIO_DEFECTO = 'admin'
CONTRASENA_DEFECTO = 'admin'
RUTA_USUARIOS = 'usuarios.json'
COLOR_FONDO_OSCURO = '#1E1E1E'
COLOR_MARCO_OSCURO = '#2D2D30'
COLOR_TEXTO_CLARO = '#D4D4D4'
COLOR_ACCION_PRIMARIA = '#FF8C00'
COLOR_ACCENTO_USUARIO = '#9CDCFE'
COLOR_ADVERTENCIA = '#CE9178'

#Principal
class SistemaFAT:

    def __init__(self):
        os.makedirs(DIR_FAT, exist_ok=True)
        os.makedirs(DIR_DATOS, exist_ok=True)
        self.usuarios_registrados = self._cargar_usuarios()
        self.usuario_actual = None

    def _cargar_usuarios(self):
        if not os.path.exists(RUTA_USUARIOS):
            return {PROPIETARIO_DEFECTO: self._hash_contrasena(CONTRASENA_DEFECTO)}
        try:
            with open(RUTA_USUARIOS, 'r') as f:
                usuarios = json.load(f)
                if PROPIETARIO_DEFECTO not in usuarios:
                    usuarios[PROPIETARIO_DEFECTO] = self._hash_contrasena(CONTRASENA_DEFECTO)
                return usuarios
        except Exception:
            return {PROPIETARIO_DEFECTO: self._hash_contrasena(CONTRASENA_DEFECTO)}

    def _guardar_usuarios(self):
        with open(RUTA_USUARIOS, 'w') as f:
            json.dump(self.usuarios_registrados, f, indent=4)

    def _hash_contrasena(self, contrasena):
        return contrasena[::-1] + '_hash'

    def verificar_credenciales(self, nombre_usuario, contrasena):
        nombre_usuario = nombre_usuario.lower()
        if nombre_usuario in self.usuarios_registrados:
            contrasena_hash = self._hash_contrasena(contrasena)
            return self.usuarios_registrados[nombre_usuario] == contrasena_hash
        return False

    def registrar_usuario(self, nombre_usuario, contrasena):
        nombre_usuario = nombre_usuario.lower()
        if nombre_usuario not in self.usuarios_registrados:
            self.usuarios_registrados[nombre_usuario] = self._hash_contrasena(contrasena)
            self._guardar_usuarios()
            return True
        return False

    def _guardar_entrada_fat(self, nombre_archivo, entrada):
        ruta = os.path.join(DIR_FAT, f"{nombre_archivo}.json")
        with open(ruta, 'w') as f:
            json.dump(entrada, f, indent=4)

    def _cargar_entrada_fat(self, nombre_archivo):
        ruta = os.path.join(DIR_FAT, f"{nombre_archivo}.json")
        if not os.path.exists(ruta):
            return None
        with open(ruta, 'r') as f:
            return json.load(f)

    def _guardar_bloque_datos(self, nombre_bloque, datos_bloque):
        ruta = os.path.join(DIR_DATOS, f"{nombre_bloque}.json")
        with open(ruta, 'w') as f:
            json.dump(datos_bloque, f, indent=4)
        return ruta

    def _eliminar_bloque_datos(self, ruta_bloque):
        if os.path.exists(ruta_bloque):
            os.remove(ruta_bloque)

    def _generar_bloques(self, contenido):
        bloques = [contenido[i:i + TAMAÑO_BLOQUE] for i in range(0, len(contenido), TAMAÑO_BLOQUE)]
        timestamp = int(time.time() * 1000)
        referencias_bloque = []
        for i, datos_bloque in enumerate(bloques):
            nombre_bloque = f"bloque_{timestamp}_{i}"
            ruta_bloque = os.path.join(DIR_DATOS, f"{nombre_bloque}.json")
            siguiente_ruta = os.path.join(DIR_DATOS, f"bloque_{timestamp}_{i+1}.json") if i < len(bloques) - 1 else None
            entrada_bloque = {
                "datos": datos_bloque,
                "siguiente_archivo": siguiente_ruta,
                "eof": (i == len(bloques) - 1)
            }
            self._guardar_bloque_datos(nombre_bloque, entrada_bloque)
            referencias_bloque.append(ruta_bloque)
        return referencias_bloque

    def _leer_contenido_completo(self, ruta_primer_bloque):
        ruta_actual = ruta_primer_bloque
        contenido_completo = ""
        rutas_bloques = []
        while ruta_actual:
            try:
                with open(ruta_actual, 'r') as f: bloque = json.load(f)
            except Exception:
                break

            contenido_completo += bloque["datos"]
            rutas_bloques.append(ruta_actual)
            if bloque["eof"]:
                ruta_actual = None
            else:
                ruta_actual = bloque["siguiente_archivo"]
        return contenido_completo, rutas_bloques

    def crear_archivo(self, nombre_archivo, contenido):
        if self._cargar_entrada_fat(nombre_archivo):
            return False, "El archivo ya existe."
        propietario_archivo = self.usuario_actual
        if not propietario_archivo:
            return False, "Usuario no logueado."
        rutas_bloques = self._generar_bloques(contenido)
        if not rutas_bloques:
            return False, "El contenido del archivo es inválido."
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entrada_fat = {
            "nombre": nombre_archivo,
            "ruta_datos_inicial": rutas_bloques[0],
            "estado_papelera": False,
            "cant_caracteres": len(contenido),
            "fecha_creacion": ahora,
            "fecha_modificacion": ahora,
            "fecha_eliminacion": None,
            "propietario": propietario_archivo,
            "permisos": {"lectura": [propietario_archivo], "escritura": [propietario_archivo]}
        }
        self._guardar_entrada_fat(nombre_archivo, entrada_fat)
        return True, "Archivo creado exitosamente."

    def listar_archivos(self, incluir_eliminados=False):
        archivos = []
        for nombre_archivo_json in os.listdir(DIR_FAT):
            if nombre_archivo_json.endswith(".json"):
                nombre = nombre_archivo_json.replace(".json", "")
                entrada = self._cargar_entrada_fat(nombre)
                if entrada and (incluir_eliminados or not entrada.get("estado_papelera", False)):
                    archivos.append(entrada)
        return archivos

    def obtener_contenido_archivo(self, nombre_archivo):
        entrada = self._cargar_entrada_fat(nombre_archivo)
        if not entrada or entrada.get("estado_papelera"):
            return None, "Archivo no encontrado o en papelera."
        if not self.verificar_permisos(nombre_archivo, "lectura"):
            return None, "Permiso de lectura denegado."
        contenido, _ = self._leer_contenido_completo(entrada["ruta_datos_inicial"])
        metadata = {
            "Nombre": entrada["nombre"],
            "Propietario": entrada["propietario"],
            "Tamaño (chars)": entrada["cant_caracteres"],
            "Creación": entrada["fecha_creacion"],
            "Modificación": entrada["fecha_modificacion"],
            "Permisos (Lectura)": ", ".join(entrada["permisos"]["lectura"]),
            "Permisos (Escritura)": ", ".join(entrada["permisos"]["escritura"]),
        }
        return metadata, contenido

    def modificar_archivo(self, nombre_archivo, nuevo_contenido):
        entrada = self._cargar_entrada_fat(nombre_archivo)
        if not entrada or entrada.get("estado_papelera"):
            return False, "Archivo no encontrado o en papelera."
        if not self.verificar_permisos(nombre_archivo, "escritura"):
            return False, "Permiso de escritura denegado."
        _, rutas_bloques_viejas = self._leer_contenido_completo(entrada["ruta_datos_inicial"])
        for ruta in rutas_bloques_viejas: self._eliminar_bloque_datos(ruta)

        rutas_bloques_nuevas = self._generar_bloques(nuevo_contenido)
        if not rutas_bloques_nuevas:
            return False, "Error: El nuevo contenido del archivo es inválido."

        entrada["ruta_datos_inicial"] = rutas_bloques_nuevas[0]
        entrada["cant_caracteres"] = len(nuevo_contenido)
        entrada["fecha_modificacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._guardar_entrada_fat(nombre_archivo, entrada)
        return True, "Archivo modificado exitosamente."

    def eliminar_archivo(self, nombre_archivo):
        entrada = self._cargar_entrada_fat(nombre_archivo)
        if not entrada or entrada.get("estado_papelera"):
            return False, "Error: Archivo no encontrado o ya en papelera."
        if entrada["propietario"] != self.usuario_actual:
            return False, "Error: Solo el propietario puede eliminar el archivo."

        entrada["estado_papelera"] = True
        entrada["fecha_eliminacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._guardar_entrada_fat(nombre_archivo, entrada)
        return True, "Archivo movido a la papelera."

    def recuperar_archivo(self, nombre_archivo):
        entrada = self._cargar_entrada_fat(nombre_archivo)
        if not entrada or not entrada.get("estado_papelera"):
            return False, "Archivo no encontrado o no está en papelera."
        if entrada["propietario"] != self.usuario_actual:
            return False, "Solo el propietario puede recuperar el archivo."
        entrada["estado_papelera"] = False
        entrada["fecha_eliminacion"] = None
        entrada["fecha_modificacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._guardar_entrada_fat(nombre_archivo, entrada)
        return True, "Archivo recuperado exitosamente."

    def verificar_permisos(self, nombre_archivo, tipo_permiso):
        entrada = self._cargar_entrada_fat(nombre_archivo)
        if not entrada: return False
        if self.usuario_actual == PROPIETARIO_DEFECTO: return True
        if self.usuario_actual == entrada["propietario"]: return True
        return self.usuario_actual in entrada["permisos"].get(tipo_permiso, [])

    def asignar_permisos(self, nombre_archivo, usuario_destino, tipo_permiso, accion="agregar"):
        entrada = self._cargar_entrada_fat(nombre_archivo)
        if not entrada: return False, "Archivo no encontrado."
        if self.usuario_actual != entrada["propietario"] and self.usuario_actual != PROPIETARIO_DEFECTO:
            return False, "Solo el propietario o el administrador pueden modificar permisos."
        lista_permisos = entrada["permisos"].get(tipo_permiso)
        if usuario_destino == entrada["propietario"]:
            return False, "No puede modificar los permisos del propietario desde esta interfaz."
        if accion == "agregar":
            if usuario_destino not in lista_permisos:
                lista_permisos.append(usuario_destino)
                self._guardar_entrada_fat(nombre_archivo, entrada)
                return True, f"Permiso de '{tipo_permiso}' asignado a {usuario_destino}."
            return False, f"El usuario {usuario_destino} ya tiene permiso de '{tipo_permiso}'."
        elif accion == "revocar":
            if usuario_destino in lista_permisos:
                lista_permisos.remove(usuario_destino)
                self._guardar_entrada_fat(nombre_archivo, entrada)
                return True, f"Permiso de '{tipo_permiso}' revocado a {usuario_destino}."
            return False, f"El usuario {usuario_destino} no tenía permiso de '{tipo_permiso}'."
        return False, "Acción de permiso no válida."

#INterfaz
class InterfazFAT:

    def __init__(self, master):
        self.master = master
        self.sistema_fat = SistemaFAT()
        self.var_usuario_actual = tk.StringVar(master, value="No Logueado")
        self.style = ttk.Style()
        self.style.theme_use('clam')
        master.config(bg=COLOR_FONDO_OSCURO)
        master.geometry("750x550")
        self.style.configure('.', background=COLOR_FONDO_OSCURO, foreground=COLOR_TEXTO_CLARO)
        self.style.configure('TLabel', background=COLOR_FONDO_OSCURO, foreground=COLOR_TEXTO_CLARO)
        self.style.configure('TFrame', background=COLOR_FONDO_OSCURO)
        self.style.configure('TLabelframe', background=COLOR_MARCO_OSCURO, foreground=COLOR_ACCENTO_USUARIO)
        self.style.configure('TLabelframe.Label', background=COLOR_MARCO_OSCURO, foreground=COLOR_ACCENTO_USUARIO)
        self.style.configure('TButton', background=COLOR_ACCION_PRIMARIA, foreground=COLOR_FONDO_OSCURO, font=('Helvetica', 10, 'bold'), bordercolor=COLOR_ACCION_PRIMARIA, borderwidth=0, relief='flat')
        self.style.map('TButton', background=[('active', COLOR_ACCION_PRIMARIA)])
        self._centrar_ventana(master, ancho=750, alto=550)
        self.login_frame = None
        self._mostrar_login_frame()

    def _centrar_ventana(self, ventana, ancho=750, alto=550):
        ventana.update_idletasks()
        w = ancho
        h = alto
        ws = ventana.winfo_screenwidth()
        hs = ventana.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        ventana.geometry(f'{w}x{h}+{x}+{y}')

    def _limpiar_ventana(self):
        for widget in self.master.winfo_children():
            widget.destroy()

    def _cambiar_usuario_en_sistema(self, nuevo_usuario):
        nuevo_usuario = nuevo_usuario.lower()
        self.sistema_fat.usuario_actual = nuevo_usuario
        self.var_usuario_actual.set(nuevo_usuario)
        self.master.title(f"Sistema FAT - Usuario: {nuevo_usuario}")
        self._configurar_interfaz_principal()

    def _mostrar_login_frame(self):
        self.sistema_fat.usuario_actual = None
        self.var_usuario_actual.set("No Logueado")
        self._limpiar_ventana()
        self.master.title("Sistema FAT - Inicio de Sesión")
        self.master.geometry("500x300")
        self._centrar_ventana(self.master, ancho=500, alto=300)
        self.login_frame = ttk.Frame(self.master, padding=30)
        self.login_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        ttk.Label(self.login_frame, text="Inicio de Sesión", font=('Helvetica', 16, 'bold'), foreground=COLOR_ACCENTO_USUARIO).grid(row=0, column=0, columnspan=2, pady=20)
        ttk.Label(self.login_frame, text="Usuario:").grid(row=1, column=0, padx=10, pady=5, sticky='w')
        ttk.Label(self.login_frame, text="Contraseña:").grid(row=2, column=0, padx=10, pady=5, sticky='w')

        entry_usuario = tk.Entry(self.login_frame, bg=COLOR_MARCO_OSCURO, fg=COLOR_TEXTO_CLARO, insertbackground=COLOR_ACCION_PRIMARIA)
        entry_usuario.grid(row=1, column=1, padx=10, pady=5)
        entry_contrasena = tk.Entry(self.login_frame, show="*", bg=COLOR_MARCO_OSCURO, fg=COLOR_TEXTO_CLARO, insertbackground=COLOR_ACCION_PRIMARIA)
        entry_contrasena.grid(row=2, column=1, padx=10, pady=5)
        entry_usuario.focus()
        self.master.bind('<Return>', lambda event: self._intentar_login_frame(entry_usuario.get(), entry_contrasena.get()))

        def intentar_login_wrapper():
            self._intentar_login_frame(entry_usuario.get(), entry_contrasena.get())

        ttk.Button(self.login_frame, text="Iniciar Sesión / Registrar", command=intentar_login_wrapper).grid(row=3, column=0, columnspan=2, pady=20)

    def _intentar_login_frame(self, usuario, contrasena):
        usuario = usuario.strip().lower()

        if not usuario or not contrasena:
            messagebox.showwarning("Debe ingresar usuario y contraseña.")
            return

        if usuario not in self.sistema_fat.usuarios_registrados:
            if messagebox.askyesno("Nuevo Usuario", f"El usuario '{usuario}' no existe. ¿Desea registrarlo con esta contraseña?"):
                self.sistema_fat.registrar_usuario(usuario, contrasena)
                messagebox.showinfo("Registro exitoso", f"Usuario '{usuario}' registrado y logueado.")
                self._cambiar_usuario_en_sistema(usuario)
            else:
                messagebox.showerror("Error", "Registro cancelado.")

        elif self.sistema_fat.verificar_credenciales(usuario, contrasena):
            messagebox.showinfo(f"Bienvenido, {usuario}.")
            self._cambiar_usuario_en_sistema(usuario)
        else:
            messagebox.showerror("Error", "Contraseña incorrecta.")

    def _mostrar_dialogo_cambio_usuario(self):
        usuarios_registrados = sorted(list(self.sistema_fat.usuarios_registrados.keys()))
        dialogo = tk.Toplevel(self.master)
        dialogo.title("Cambiar Usuario")
        dialogo.config(bg=COLOR_FONDO_OSCURO)
        var_usuario_seleccionado = tk.StringVar(dialogo)
        var_usuario_seleccionado.set(self.sistema_fat.usuario_actual)
        tk.Label(dialogo, text="Seleccione el nuevo usuario:", bg=COLOR_FONDO_OSCURO, fg=COLOR_TEXTO_CLARO).pack(pady=5, padx=20)
        opciones_usuario = tk.OptionMenu(dialogo, var_usuario_seleccionado, *usuarios_registrados)
        opciones_usuario.config(bg=COLOR_MARCO_OSCURO, fg=COLOR_TEXTO_CLARO)
        opciones_usuario.pack(padx=20, fill='x')
        entry_contrasena = tk.Entry(dialogo, show="*", bg=COLOR_MARCO_OSCURO, fg=COLOR_TEXTO_CLARO)
        tk.Label(dialogo, text="Contraseña (si es necesario):", bg=COLOR_FONDO_OSCURO, fg=COLOR_TEXTO_CLARO).pack(pady=5, padx=20)
        entry_contrasena.pack(padx=20, fill='x')

        def confirmar_cambio():
            nuevo_usuario = var_usuario_seleccionado.get().lower()
            contrasena = entry_contrasena.get()
            usuario_actual = self.sistema_fat.usuario_actual

            if usuario_actual == PROPIETARIO_DEFECTO:
                if nuevo_usuario == usuario_actual:
                    dialogo.destroy()
                    return
                self._cambiar_usuario_en_sistema(nuevo_usuario)
                messagebox.showinfo("Éxito", f"Cambio de usuario exitoso a {nuevo_usuario}.")
                dialogo.destroy()
                return

            if self.sistema_fat.verificar_credenciales(nuevo_usuario, contrasena):
                self._cambiar_usuario_en_sistema(nuevo_usuario)
                messagebox.showinfo("Éxito", f"Cambio de usuario exitoso a {nuevo_usuario}.")
                dialogo.destroy()
            else:
                messagebox.showerror("Error de Credenciales", "Contraseña incorrecta para el usuario de destino.")

        ttk.Button(dialogo, text="Cambiar", command=confirmar_cambio).pack(pady=10)
        dialogo.update_idletasks()
        w = dialogo.winfo_width()
        h = dialogo.winfo_height()
        ws = self.master.winfo_screenwidth()
        hs = self.master.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        dialogo.geometry(f'{w}x{h}+{x}+{y}')
        dialogo.transient(self.master)
        dialogo.grab_set()

    def _configurar_interfaz_principal(self):
        self._limpiar_ventana()
        self.master.geometry("850x600")
        self._centrar_ventana(self.master, ancho=850, alto=600)
        frame_usuario = ttk.Frame(self.master, padding=10)
        frame_usuario.pack(fill='x')

        ttk.Label(frame_usuario, text="Usuario Actual:").pack(side=tk.LEFT)
        ttk.Label(frame_usuario, textvariable=self.var_usuario_actual, foreground=COLOR_ACCENTO_USUARIO, font=('Helvetica', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Button(frame_usuario, text="Cerrar Sesión", command=self._mostrar_login_frame).pack(side=tk.RIGHT, padx=5)
        ttk.Button(frame_usuario, text="Cambiar Usuario", command=self._mostrar_dialogo_cambio_usuario).pack(side=tk.RIGHT, padx=5)

        frame_lista = ttk.LabelFrame(self.master, text="Archivos en el Sistema", padding=10)
        frame_lista.pack(padx=10, pady=5, fill='both', expand=True)
        self.lista_archivos_box = tk.Listbox(frame_lista, height=15, bg=COLOR_MARCO_OSCURO, fg=COLOR_TEXTO_CLARO, selectbackground=COLOR_ACCION_PRIMARIA, selectforeground=COLOR_FONDO_OSCURO, highlightthickness=0)
        self.lista_archivos_box.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame_lista, orient="vertical")
        scrollbar.config(command=self.lista_archivos_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.lista_archivos_box.config(yscrollcommand=scrollbar.set)

        frame_botones = ttk.Frame(self.master, padding=5)
        frame_botones.pack(fill='x')
        ttk.Button(frame_botones, text="Crear Archivo", command=self.gui_crear_archivo).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(frame_botones, text="Abrir", command=self.gui_abrir_archivo).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(frame_botones, text="Modificar", command=self.gui_modificar_archivo).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(frame_botones, text="Eliminar", command=self.gui_eliminar_archivo).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(frame_botones, text="Ver Papelera", command=self.gui_ver_papelera).pack(side=tk.LEFT, padx=5, pady=5)

        self.style.configure('Special.TButton', background=COLOR_ADVERTENCIA, foreground=COLOR_FONDO_OSCURO)
        self.style.map('Special.TButton', background=[('active', COLOR_ADVERTENCIA)])
        self.boton_permisos = ttk.Button(frame_botones, text="Gestionar Permisos", command=self.gui_gestionar_permisos, style='Special.TButton')
        self.boton_permisos.pack(side=tk.LEFT, padx=5, pady=5)

        self.actualizar_estado_botones()
        self.actualizar_lista_archivos()

    def actualizar_estado_botones(self):
        es_admin = self.sistema_fat.usuario_actual == PROPIETARIO_DEFECTO
        esta_logueado = self.sistema_fat.usuario_actual is not None
        estado = tk.NORMAL if esta_logueado else tk.DISABLED

        for btn in self.master.winfo_children()[-1].winfo_children():
            if isinstance(btn, ttk.Button):
                btn.config(state=estado)

        self.boton_permisos.config(state=tk.NORMAL if es_admin else tk.DISABLED)

    def actualizar_lista_archivos(self, incluir_eliminados=False):
        self.lista_archivos_box.delete(0, tk.END)
        if not self.sistema_fat.usuario_actual:
            self.lista_archivos_box.insert(0, "Inicie sesión para ver los archivos.")
            self.lista_archivos_box.itemconfig(0, {'fg': COLOR_ADVERTENCIA})
            return

        archivos = self.sistema_fat.listar_archivos(incluir_eliminados=incluir_eliminados)

        for i, entrada_archivo in enumerate(archivos):
            estado = f"[{'ELIM' if entrada_archivo.get('estado_papelera') else 'OK'}]"
            display_text = f"{estado} {entrada_archivo['nombre']} (Propietario: {entrada_archivo['propietario']})"
            self.lista_archivos_box.insert(i, display_text)

            if entrada_archivo.get('estado_papelera'):
                self.lista_archivos_box.itemconfig(i, {'fg': COLOR_ADVERTENCIA})
            elif estado == "[OK]":
                self.lista_archivos_box.itemconfig(i, {'fg': COLOR_ACCION_PRIMARIA})


    def obtener_nombre_archivo_seleccionado(self):
        indices_seleccionados = self.lista_archivos_box.curselection()
        if not indices_seleccionados:
            messagebox.showwarning("Selección", "Por favor, selecciona un archivo de la lista.")
            return None

        texto_seleccionado = self.lista_archivos_box.get(indices_seleccionados[0]).split('(Propietario:')[0].strip()
        nombre_archivo = ' '.join(texto_seleccionado.split()[1:]).strip()
        return nombre_archivo

    def gui_crear_archivo(self):
        nombre_archivo = simpledialog.askstring("Crear Archivo", "Introduce el nombre del archivo:")
        if not nombre_archivo: return
        contenido = simpledialog.askstring("Crear Archivo", f"Introduce el contenido de '{nombre_archivo}':", initialvalue="")
        if contenido is None: return
        exito, mensaje = self.sistema_fat.crear_archivo(nombre_archivo, contenido)
        if exito:
            messagebox.showinfo("Éxito", mensaje)
            self.actualizar_lista_archivos()
        else:
            messagebox.showerror("Error", mensaje)

    def gui_abrir_archivo(self):
        nombre_archivo = self.obtener_nombre_archivo_seleccionado()
        if not nombre_archivo:
            return

        metadata, contenido_o_error = self.sistema_fat.obtener_contenido_archivo(nombre_archivo)

        if metadata:
            meta_str = "\n".join([f"    {k}: {v}" for k, v in metadata.items()])

            ventana_ver = tk.Toplevel(self.master)
            ventana_ver.title(f"Contenido de {nombre_archivo}")
            ventana_ver.config(bg=COLOR_FONDO_OSCURO)

            scrolled_text = scrolledtext.ScrolledText(ventana_ver, width=80, height=20, wrap=tk.WORD, bg=COLOR_MARCO_OSCURO, fg=COLOR_TEXTO_CLARO, insertbackground=COLOR_ACCION_PRIMARIA)
            scrolled_text.pack(padx=10, pady=10, fill='both', expand=True)
            scrolled_text.insert(tk.END, "--- METADATOS ---\n", 'titulo')
            scrolled_text.insert(tk.END, f"{meta_str}\n\n")
            scrolled_text.insert(tk.END, "--- CONTENIDO ---\n", 'titulo')
            scrolled_text.insert(tk.END, contenido_o_error)
            scrolled_text.tag_config('titulo', font=('TkDefaultFont', 10, 'bold'), foreground=COLOR_ACCENTO_USUARIO)
            scrolled_text.config(state=tk.DISABLED)

            ttk.Button(ventana_ver, text="Cerrar", command=ventana_ver.destroy).pack(pady=5)
            self._centrar_ventana(ventana_ver, ancho=600, alto=450)

        else:
            messagebox.showerror("Error al Abrir", contenido_o_error)

    def gui_modificar_archivo(self):

        nombre_archivo = self.obtener_nombre_archivo_seleccionado()
        if not nombre_archivo: return
        metadata, contenido_o_error = self.sistema_fat.obtener_contenido_archivo(nombre_archivo)

        if not metadata:
            messagebox.showerror("Error al Modificar", contenido_o_error)
            return

        ventana_mod = tk.Toplevel(self.master)
        ventana_mod.title(f"Modificar Archivo: {nombre_archivo}")
        ventana_mod.config(bg=COLOR_FONDO_OSCURO)
        tk.Label(ventana_mod, text="Edite el contenido a continuación:", bg=COLOR_FONDO_OSCURO, fg=COLOR_TEXTO_CLARO).pack(padx=10, pady=5)

        texto_area = scrolledtext.ScrolledText(ventana_mod, width=80, height=20, wrap=tk.WORD, bg=COLOR_MARCO_OSCURO, fg=COLOR_TEXTO_CLARO, insertbackground=COLOR_ACCION_PRIMARIA)
        texto_area.pack(padx=10, pady=10, fill='both', expand=True)
        texto_area.insert(tk.END, contenido_o_error)

        def guardar_cambios():
            nuevo_contenido = texto_area.get(1.0, tk.END).strip()
            exito, mensaje = self.sistema_fat.modificar_archivo(nombre_archivo, nuevo_contenido)

            if exito:
                messagebox.showinfo("Éxito", mensaje)
                self.actualizar_lista_archivos()
                ventana_mod.destroy()
            else:
                messagebox.showerror("Error al Modificar", mensaje)

        ttk.Button(ventana_mod, text="Guardar Cambios", command=guardar_cambios).pack(pady=10)
        self._centrar_ventana(ventana_mod, ancho=600, alto=450)

    def gui_eliminar_archivo(self):
        nombre_archivo = self.obtener_nombre_archivo_seleccionado()
        if not nombre_archivo:
            return

        if messagebox.askyesno("Eliminar", f"¿Estás seguro de que quieres mover '{nombre_archivo}' a la papelera?"):
            exito, mensaje = self.sistema_fat.eliminar_archivo(nombre_archivo)
            if exito:
                messagebox.showinfo("Éxito", mensaje)
                self.actualizar_lista_archivos()
            else:
                messagebox.showerror("Error al Eliminar", mensaje)

    def gui_ver_papelera(self):
        ventana_papelera = tk.Toplevel(self.master)
        ventana_papelera.title("Papelera de Reciclaje Virtual")
        ventana_papelera.config(bg=COLOR_FONDO_OSCURO)

        tk.Label(ventana_papelera, text="Archivos en Papelera:", bg=COLOR_FONDO_OSCURO, fg=COLOR_TEXTO_CLARO).pack(padx=10, pady=5)
        lista_papelera_box = tk.Listbox(ventana_papelera, height=10, width=50, bg=COLOR_MARCO_OSCURO, fg=COLOR_TEXTO_CLARO, selectbackground=COLOR_ADVERTENCIA, selectforeground=COLOR_FONDO_OSCURO)
        lista_papelera_box.pack(padx=10, pady=5)

        archivos_en_papelera = [f for f in self.sistema_fat.listar_archivos(incluir_eliminados=True) if f.get("estado_papelera")]

        for i, entrada_archivo in enumerate(archivos_en_papelera):
            lista_papelera_box.insert(i, f"[ELIM] {entrada_archivo['nombre']} (Eliminado: {entrada_archivo['fecha_eliminacion']})")
            lista_papelera_box.itemconfig(i, {'fg': COLOR_ADVERTENCIA})

        def recuperar_seleccionado():
            indices_seleccionados = lista_papelera_box.curselection()
            if not indices_seleccionados:
                messagebox.showwarning("Selección", "Por favor, selecciona un archivo para recuperar.")
                return

            texto_seleccionado = lista_papelera_box.get(indices_seleccionados[0]).split('(Eliminado:')[0].strip()
            nombre_archivo_a_recuperar = texto_seleccionado.replace('[ELIM]', '').strip()
            exito, mensaje = self.sistema_fat.recuperar_archivo(nombre_archivo_a_recuperar)

            if exito:
                messagebox.showinfo("Éxito", mensaje)
                self.actualizar_lista_archivos()
                ventana_papelera.destroy()
            else:
                messagebox.showerror("Error al Recuperar", mensaje)

        ttk.Button(ventana_papelera, text="Recuperar Archivo", command=recuperar_seleccionado).pack(pady=10)
        self._centrar_ventana(ventana_papelera, ancho=450, alto=350)


    def gui_gestionar_permisos(self):
        nombre_archivo = self.obtener_nombre_archivo_seleccionado()
        if not nombre_archivo: return
        entrada = self.sistema_fat._cargar_entrada_fat(nombre_archivo)
        if self.sistema_fat.usuario_actual != PROPIETARIO_DEFECTO:
            messagebox.showerror("Permisos", "Solo el administrador puede gestionar permisos.")
            return

        ventana_permisos = tk.Toplevel(self.master)
        ventana_permisos.title(f"Permisos de {nombre_archivo}")
        ventana_permisos.config(bg=COLOR_FONDO_OSCURO)
        tk.Label(ventana_permisos, text="Gestionar Permisos", bg=COLOR_FONDO_OSCURO, fg=COLOR_ACCENTO_USUARIO, font=('TkDefaultFont', 10, 'bold')).grid(row=0, column=0, columnspan=3, pady=5)
        usuarios_disponibles = sorted([
            u for u in self.sistema_fat.usuarios_registrados.keys() if u != entrada["propietario"]
            ])

        if not usuarios_disponibles:
            tk.Label(ventana_permisos, text="No hay otros usuarios registrados para asignar permisos.", bg=COLOR_FONDO_OSCURO, fg=COLOR_TEXTO_CLARO).grid(row=1, column=0, columnspan=3, pady=10)
            self._centrar_ventana(ventana_permisos, ancho=400, alto=200)
            return

        var_usuario = tk.StringVar(ventana_permisos, value=usuarios_disponibles[0])
        var_permiso_lectura = tk.BooleanVar(ventana_permisos)
        var_permiso_escritura = tk.BooleanVar(ventana_permisos)

        tk.Label(ventana_permisos, text="Seleccionar Usuario:", bg=COLOR_FONDO_OSCURO, fg=COLOR_TEXTO_CLARO).grid(row=1, column=0, padx=5, pady=5, sticky='w')
        opciones_usuario = tk.OptionMenu(ventana_permisos, var_usuario, *usuarios_disponibles)
        opciones_usuario.config(bg=COLOR_MARCO_OSCURO, fg=COLOR_TEXTO_CLARO)
        opciones_usuario["menu"].config(bg=COLOR_MARCO_OSCURO, fg=COLOR_TEXTO_CLARO)
        opciones_usuario.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky='we')

        def cargar_estado_permisos():
            entrada_actualizada = self.sistema_fat._cargar_entrada_fat(nombre_archivo)
            if not entrada_actualizada:
                return
            usuario_sel = var_usuario.get()
            tiene_lectura = usuario_sel in entrada_actualizada["permisos"].get("lectura", [])
            tiene_escritura = usuario_sel in entrada_actualizada["permisos"].get("escritura", [])
            var_permiso_lectura.set(tiene_lectura)
            var_permiso_escritura.set(tiene_escritura)

        var_usuario.trace_add("write", lambda *args: cargar_estado_permisos())
        tk.Label(ventana_permisos, text="Permisos:", bg=COLOR_FONDO_OSCURO, fg=COLOR_TEXTO_CLARO).grid(row=2, column=0, padx=5, pady=5, sticky='w')
        tk.Checkbutton(ventana_permisos, text="Lectura", variable=var_permiso_lectura, bg=COLOR_FONDO_OSCURO, fg=COLOR_TEXTO_CLARO, selectcolor=COLOR_FONDO_OSCURO).grid(row=2, column=1, padx=5, pady=5, sticky='w')
        tk.Checkbutton(ventana_permisos, text="Escritura", variable=var_permiso_escritura, bg=COLOR_FONDO_OSCURO, fg=COLOR_TEXTO_CLARO, selectcolor=COLOR_FONDO_OSCURO).grid(row=2, column=2, padx=5, pady=5, sticky='w')

        cargar_estado_permisos()

        def confirmar_cambios_central():
            usuario_destino = var_usuario.get()
            entrada_actualizada = self.sistema_fat._cargar_entrada_fat(nombre_archivo)
            if not entrada_actualizada:
                messagebox.showerror("Error", "Archivo no encontrado para actualizar permisos.")
                return

            tiene_lectura_actual = usuario_destino in entrada_actualizada["permisos"].get("lectura", [])
            if var_permiso_lectura.get() and not tiene_lectura_actual:
                self.sistema_fat.asignar_permisos(nombre_archivo, usuario_destino, "lectura", "agregar")
            elif not var_permiso_lectura.get() and tiene_lectura_actual:
                self.sistema_fat.asignar_permisos(nombre_archivo, usuario_destino, "lectura", "revocar")

            tiene_escritura_actual = usuario_destino in entrada_actualizada["permisos"].get("escritura", [])
            if var_permiso_escritura.get() and not tiene_escritura_actual:
                self.sistema_fat.asignar_permisos(nombre_archivo, usuario_destino, "escritura", "agregar")
            elif not var_permiso_escritura.get() and tiene_escritura_actual:
                self.sistema_fat.asignar_permisos(nombre_archivo, usuario_destino, "escritura", "revocar")

            messagebox.showinfo("Éxito", f"Permisos de '{usuario_destino}' actualizados correctamente.")
            ventana_permisos.destroy()

        ttk.Button(ventana_permisos, text="Aplicar Cambios", command=confirmar_cambios_central).grid(row=4, column=0, columnspan=3, pady=10)
        self._centrar_ventana(ventana_permisos, ancho=450, alto=300)

root = tk.Tk()
app = InterfazFAT(root)
root.mainloop()