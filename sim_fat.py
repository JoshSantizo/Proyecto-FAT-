import json
import os
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext, ttk
from configuracion import TAMAÑO_BLOQUE, DIR_FAT, DIR_DATOS, PROPIETARIO_DEFECTO, RUTA_USUARIOS

class SistemaFAT:
    def __init__(self):
        os.makedirs(DIR_FAT, exist_ok=True)
        os.makedirs(DIR_DATOS, exist_ok=True)
        self.usuarios_registrados = {PROPIETARIO_DEFECTO}
        self.usuario_actual = PROPIETARIO_DEFECTO
        self._cargar_usuarios = lambda: {PROPIETARIO_DEFECTO}
        self._guardar_usuarios = lambda: None
        self.registrar_usuario = lambda x: True

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

    def _cargar_bloque_datos(self, ruta_bloque):
        if not os.path.exists(ruta_bloque): return None
        try:
            with open(ruta_bloque, 'r') as f: return json.load(f)
        except Exception: return None

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
            bloque = self._cargar_bloque_datos(ruta_actual)
            if not bloque: break
            contenido_completo += bloque["datos"]
            rutas_bloques.append(ruta_actual)
            if bloque["eof"]:
                ruta_actual = None
            else:
                ruta_actual = bloque["siguiente_archivo"]
        return contenido_completo, rutas_bloques

    def crear_archivo(self, nombre_archivo, contenido, propietario=PROPIETARIO_DEFECTO):
        if self._cargar_entrada_fat(nombre_archivo):
            return False, "El archivo ya existe."
        propietario_archivo = self.usuario_actual
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
            return None, "Error: Archivo no encontrado o en papelera."
        if self.usuario_actual != entrada["propietario"] and self.usuario_actual != PROPIETARIO_DEFECTO:
            return None, "Error: Permiso de lectura denegado (Solo el propietario puede leer)."

        contenido, _ = self._leer_contenido_completo(entrada["ruta_datos_inicial"])
        metadata = {
            "Nombre": entrada["nombre"], "Propietario": entrada["propietario"],
            "Tamaño (chars)": entrada["cant_caracteres"], "Creación": entrada["fecha_creacion"],
            "Modificación": entrada["fecha_modificacion"],
            "Permisos": "Solo Propietario"
        }
        return metadata, contenido

    def modificar_archivo(self, nombre_archivo, nuevo_contenido):
        entrada = self._cargar_entrada_fat(nombre_archivo)
        if not entrada or entrada.get("estado_papelera"):
            return False, "Archivo no encontrado o en papelera."

        if self.usuario_actual != entrada["propietario"] and self.usuario_actual != PROPIETARIO_DEFECTO:
            return False, "Permiso de escritura denegado (Solo el propietario puede modificar)."

        _, rutas_bloques_viejas = self._leer_contenido_completo(entrada["ruta_datos_inicial"])
        for ruta in rutas_bloques_viejas:
            self._eliminar_bloque_datos(ruta)
        rutas_bloques_nuevas = self._generar_bloques(nuevo_contenido)
        if not rutas_bloques_nuevas: return False, "Contenido inválido."
        entrada["ruta_datos_inicial"] = rutas_bloques_nuevas[0]
        entrada["cant_caracteres"] = len(nuevo_contenido)
        entrada["fecha_modificacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._guardar_entrada_fat(nombre_archivo, entrada)
        return True, "Archivo modificado exitosamente."

    def eliminar_archivo(self, nombre_archivo):
        entrada = self._cargar_entrada_fat(nombre_archivo)
        if not entrada or entrada.get("estado_papelera"):
            return False, "Archivo no encontrado o ya en papelera."
        if entrada["propietario"] != self.usuario_actual:
            return False, "Solo el propietario puede eliminar el archivo."
        entrada["estado_papelera"] = True
        entrada["fecha_eliminacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._guardar_entrada_fat(nombre_archivo, entrada)
        return True, "Archivo movido a la papelera."

    #FUnciones Pendientes
    def recuperar_archivo(self, nombre_archivo): return False, "No implementado aún"
    def verificar_permisos(self, nombre_archivo, tipo_permiso): return True
    def asignar_permisos(self, nombre_archivo, usuario_destino, tipo_permiso, accion="agregar"): return False, "No implementado aún"


#INterfaz
class InterfazFAT:
    def __init__(self, master):
        self.master = master
        self.sistema_fat = SistemaFAT()
        self.master.title("FAT")
        self.var_usuario_actual = tk.StringVar(master, value=PROPIETARIO_DEFECTO)
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self._configurar_interfaz()
        self._mostrar_dialogo_login()

    def _centrar_ventana(self, ventana, ancho=None, alto=None):
        ventana.update_idletasks()
        w = ancho if ancho else ventana.winfo_width()
        h = alto if alto else ventana.winfo_height()
        ws = ventana.winfo_screenwidth()
        hs = ventana.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        ventana.geometry(f'{w}x{h}+{x}+{y}')
        ventana.transient(self.master)
        ventana.grab_set()

    def _cambiar_usuario_en_sistema(self, nuevo_usuario):
        self.sistema_fat.usuario_actual = nuevo_usuario
        self.var_usuario_actual.set(nuevo_usuario)
        self.master.title(f"Simulador FAT - Usuario: {nuevo_usuario}")
        self.actualizar_lista_archivos()

    def _mostrar_dialogo_cambio_usuario(self):messagebox.showinfo("Cambio de Usuario", "")

    def _mostrar_dialogo_login(self):
        usuario = simpledialog.askstring("Inicio de Sesión", "Ingrese su nombre de usuario:")
        if not usuario:
            self.master.quit()
            return
        self._cambiar_usuario_en_sistema(usuario.strip().lower())
        self.master.deiconify()

    def _configurar_interfaz(self):
        frame_usuario = ttk.Frame(self.master, padding=10)
        frame_usuario.pack(fill='x')
        ttk.Label(frame_usuario, text="Usuario Actual:").pack(side=tk.LEFT)
        ttk.Label(frame_usuario, textvariable=self.var_usuario_actual).pack(side=tk.LEFT)
        ttk.Button(frame_usuario, text="Cambiar Usuario", command=self._mostrar_dialogo_cambio_usuario).pack(side=tk.RIGHT, padx=5)
        frame_lista = ttk.LabelFrame(self.master, text="Archivos en el Sistema", padding=10)
        frame_lista.pack(padx=10, pady=5, fill='both', expand=True)
        self.lista_archivos_box = tk.Listbox(frame_lista, height=15)
        self.lista_archivos_box.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame_lista, orient="vertical", command=self.lista_archivos_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.lista_archivos_box.config(yscrollcommand=scrollbar.set)
        frame_botones = ttk.Frame(self.master, padding=5)
        frame_botones.pack(fill='x')
        ttk.Button(frame_botones, text="Crear Archivo", command=self.gui_crear_archivo).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(frame_botones, text="Abrir/Ver", command=self.gui_abrir_archivo).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(frame_botones, text="Modificar", command=self.gui_modificar_archivo).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(frame_botones, text="Eliminar (Papelera)", command=self.gui_eliminar_archivo).pack(side=tk.LEFT, padx=5, pady=5)
        self.actualizar_lista_archivos()

    def actualizar_estado_botones(self):
        pass

    def actualizar_lista_archivos(self, incluir_eliminados=False):
        self.lista_archivos_box.delete(0, tk.END)
        archivos = self.sistema_fat.listar_archivos(incluir_eliminados=incluir_eliminados)
        for i, entrada_archivo in enumerate(archivos):
            estado = f"[{'ELIM' if entrada_archivo.get('estado_papelera') else 'OK'}]"
            display_text = f"{estado} {entrada_archivo['nombre']} (Propietario: {entrada_archivo['propietario']})"
            self.lista_archivos_box.insert(i, display_text)
            if entrada_archivo.get('estado_papelera'):self.lista_archivos_box.itemconfig(i, {'fg': 'red'}) 
            elif estado == "[OK]":self.lista_archivos_box.itemconfig(i, {'fg': 'black'})


    def obtener_nombre_archivo_seleccionado(self):
        indices_seleccionados = self.lista_archivos_box.curselection()
        if not indices_seleccionados:
            messagebox.showwarning("Selección", "Por favor, selecciona un archivo de la lista.")
            return None
        texto_seleccionado = self.lista_archivos_box.get(indices_seleccionados[0]).split('(Propietario:')[0].strip()
        return ' '.join(texto_seleccionado.split()[1:]).strip()

    def gui_crear_archivo(self):
        nombre_archivo = simpledialog.askstring("Crear Archivo", "Introduce el nombre del archivo:")
        if not nombre_archivo: return
        contenido = simpledialog.askstring("Crear Archivo", f"Introduce el contenido de '{nombre_archivo}':", initialvalue="")
        if contenido is None: return
        exito, mensaje = self.sistema_fat.crear_archivo(nombre_archivo, contenido, propietario=self.sistema_fat.usuario_actual)
        if exito:
            messagebox.showinfo("Éxito", mensaje)
            self.actualizar_lista_archivos()
        else:
            messagebox.showerror("Error", mensaje)

    def gui_abrir_archivo(self):
        nombre_archivo = self.obtener_nombre_archivo_seleccionado()
        if not nombre_archivo: return
        metadata, contenido_o_error = self.sistema_fat.obtener_contenido_archivo(nombre_archivo)
        if metadata:
            meta_str = "\n".join([f"    {k}: {v}" for k, v in metadata.items()])
            messagebox.showinfo(f"Contenido de {nombre_archivo}",
                                f"--- METADATOS ---\n{meta_str}\n\n--- CONTENIDO ---\n{contenido_o_error}")
        else:
            messagebox.showerror("Error al Abrir", contenido_o_error)

    def gui_modificar_archivo(self):
        nombre_archivo = self.obtener_nombre_archivo_seleccionado()
        if not nombre_archivo: return
        metadata, contenido_o_error = self.sistema_fat.obtener_contenido_archivo(nombre_archivo)
        if not metadata:
            messagebox.showerror("Error al Modificar", contenido_o_error)
            return
        nuevo_contenido = simpledialog.askstring("Modificar Archivo", f"Edita el contenido de '{nombre_archivo}':", initialvalue=contenido_o_error)
        if nuevo_contenido is None: return
        exito, mensaje = self.sistema_fat.modificar_archivo(nombre_archivo, nuevo_contenido)
        if exito:
            messagebox.showinfo("Éxito", mensaje)
            self.actualizar_lista_archivos()
        else:
            messagebox.showerror("Error al Modificar", mensaje)

    def gui_eliminar_archivo(self):
        nombre_archivo = self.obtener_nombre_archivo_seleccionado()
        if not nombre_archivo: return
        if messagebox.askyesno("Eliminar", f"¿Seguro que quieres mover '{nombre_archivo}' a la papelera?"):
            exito, mensaje = self.sistema_fat.eliminar_archivo(nombre_archivo)
            if exito:
                messagebox.showinfo("Éxito", mensaje)
                self.actualizar_lista_archivos()
            else:
                messagebox.showerror("Error al Eliminar", mensaje)
    def gui_ver_papelera(self):
        messagebox.showinfo("Papelera", "")

    def gui_gestionar_permisos(self):
        messagebox.showinfo("Permisos", "")

root = tk.Tk()
root.title("Simulador FAT")
app = InterfazFAT(root)
root.mainloop()