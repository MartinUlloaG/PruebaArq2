import { Navigate, Route, Routes } from 'react-router-dom'

import Marco from './vistas/Marco'
import RutaProtegida from './vistas/RutaProtegida'
import VistaIngreso from './vistas/VistaIngreso'
import Inicio from './vistas/Inicio'
import Catalogo from './vistas/Catalogo'
import VistaInventario from './vistas/VistaInventario'
import VistaPedidos from './vistas/VistaPedidos'
import VistaRetornoPago from './vistas/VistaRetornoPago'
import VistaUsuarios from './vistas/VistaUsuarios'

export default function App() {
  return (
    <Routes>
      <Route path="/ingresar" element={<VistaIngreso />} />
      <Route
        element={
          <RutaProtegida>
            <Marco />
          </RutaProtegida>
        }
      >
        <Route index element={<Inicio />} />
        <Route
          path="catalogo"
          element={
            <RutaProtegida roles={['cliente']}>
              <Catalogo />
            </RutaProtegida>
          }
        />
        <Route
          path="pedidos"
          element={
            <RutaProtegida roles={['cliente']}>
              <VistaPedidos />
            </RutaProtegida>
          }
        />
        <Route
          path="pago/retorno"
          element={
            <RutaProtegida roles={['cliente']}>
              <VistaRetornoPago />
            </RutaProtegida>
          }
        />
        <Route
          path="inventario"
          element={
            <RutaProtegida roles={['operador', 'administrador']}>
              <VistaInventario />
            </RutaProtegida>
          }
        />
        <Route
          path="usuarios"
          element={
            <RutaProtegida roles={['administrador']}>
              <VistaUsuarios />
            </RutaProtegida>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
