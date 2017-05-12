/*
 *  target_table_devices_impl.h
 *
 *  This file is part of NEST.
 *
 *  Copyright (C) 2004 The NEST Initiative
 *
 *  NEST is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  NEST is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with NEST.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

#ifndef TARGET_TABLE_DEVICES_IMPL_H
#define TARGET_TABLE_DEVICES_IMPL_H

// Includes from nestkernel:
#include "target_table_devices.h"
#include "kernel_manager.h"
#include "vp_manager_impl.h"
#include "model_manager.h"
#include "node.h"
#include "connector_base.h"

inline void
nest::TargetTableDevices::add_connection_to_device( Node& source,
  Node& target,
  const index s_gid,
  const thread tid,
  const synindex syn_id,
  const double d,
  const double w )
{
  const index lid = kernel().vp_manager.gid_to_lid( s_gid );
  assert( lid < target_to_devices_[ tid ]->size() );
  // make sure this neuron has support for all synapse types
  ( *target_to_devices_[ tid ] )[ lid ].resize( kernel().model_manager.get_num_synapse_prototypes(), NULL );
  // add connection to device
  kernel()
    .model_manager.get_synapse_prototype( syn_id, tid )
    .add_connection_5g(
      source, target, &( *target_to_devices_[ tid ] )[ lid ], syn_id, d, w );
}

inline void
nest::TargetTableDevices::add_connection_to_device( Node& source,
  Node& target,
  const index s_gid,
  const thread tid,
  const synindex syn_id,
  const DictionaryDatum& p,
  const double d,
  const double w )
{
  const index lid = kernel().vp_manager.gid_to_lid( s_gid );
  assert( lid < target_to_devices_[ tid ]->size() );
  // make sure this neuron has support for all synapse types
  ( *target_to_devices_[ tid ] )[ lid ].resize( kernel().model_manager.get_num_synapse_prototypes(), NULL );
  // add connection to device
  kernel()
    .model_manager.get_synapse_prototype( syn_id, tid )
    .add_connection_5g(
      source, target, &( *target_to_devices_[ tid ] )[ lid ], syn_id, p, d, w );
}

// TODO@5g: unify these two functions below?
inline void
nest::TargetTableDevices::add_connection_from_device( Node& source,
  Node& target,
  const index s_gid,
  const thread tid,
  const synindex syn_id,
  const double d,
  const double w )
{
  const index ldid = source.get_local_device_id();
  assert( ldid != invalid_index );
  assert( ldid < target_from_devices_[ tid ]->size() );
  // make sure this device has support for all synapse types
  ( *target_from_devices_[ tid ] )[ ldid ].resize( kernel().model_manager.get_num_synapse_prototypes(), NULL );
  // add connection from device
  kernel()
    .model_manager.get_synapse_prototype( syn_id, tid )
    .add_connection_5g(
      source, target, &( *target_from_devices_[ tid ] )[ ldid ], syn_id, d, w );
  // store gid of sending device
  ( *sending_devices_gids_[ tid ] )[ ldid ] = source.get_gid();
}

inline void
nest::TargetTableDevices::add_connection_from_device( Node& source,
  Node& target,
  const index s_gid,
  const thread tid,
  const synindex syn_id,
  const DictionaryDatum& p,
  const double d,
  const double w )
{
  const index ldid = source.get_local_device_id();
  assert( ldid != invalid_index );
  assert( ldid < target_from_devices_[ tid ]->size() );
  // make sure this device has support for all synapse types
  ( *target_from_devices_[ tid ] )[ ldid ].resize( kernel().model_manager.get_num_synapse_prototypes(), NULL );
  // add connection from device
  kernel()
    .model_manager.get_synapse_prototype( syn_id, tid )
    .add_connection_5g(
      source, target, &( *target_from_devices_[ tid ] )[ ldid ], syn_id, p, d, w );
  // store gid of sending device
  ( *sending_devices_gids_[ tid ] )[ ldid ] = source.get_gid();
}

inline void
nest::TargetTableDevices::send_to_device( const thread tid,
  const index s_gid,
  Event& e,
  const std::vector< ConnectorModel* >& cm )
{
  const index lid = kernel().vp_manager.gid_to_lid( s_gid );
  for ( std::vector< ConnectorBase* >::iterator it = ( *target_to_devices_[ tid ] )[ lid ].begin();
        it != ( *target_to_devices_[ tid ] )[ lid ].end(); ++it )
  {
    if ( *it != NULL )
    {
      ( *it )->send_to_all( e, tid, cm );
    }
  }
}

inline void
nest::TargetTableDevices::send_from_device( const thread tid,
  const index ldid,
  Event& e,
  const std::vector< ConnectorModel* >& cm )
{
  for ( std::vector< ConnectorBase* >::iterator it = ( *target_from_devices_[ tid ] )[ ldid ].begin();
        it != ( *target_from_devices_[ tid ] )[ ldid ].end(); ++it )
  {
    if ( *it != NULL )
    {
      ( *it )->send_to_all( e, tid, cm );
    }
  }
}

inline void
nest::TargetTableDevices::get_synapse_status_to_device( const thread tid,
  const index source_gid,
  const synindex syn_id,
  DictionaryDatum& d,
  const port p ) const
{
  const index lid = kernel().vp_manager.gid_to_lid( source_gid );
  ( *target_to_devices_[ tid ] )[ lid ][ syn_id ]->get_synapse_status( syn_id, d, p );
}

inline void
nest::TargetTableDevices::get_synapse_status_from_device( const thread tid,
  const index ldid,
  const synindex syn_id,
  DictionaryDatum& d,
  const port p ) const
{
  ( *target_from_devices_[ tid ] )[ ldid ][ syn_id ]->get_synapse_status( syn_id, d, p );
}

inline void
nest::TargetTableDevices::set_synapse_status_to_device( const thread tid,
  const index source_gid,
  const synindex syn_id,
  ConnectorModel& cm,
  const DictionaryDatum& d,
  const port p )
{
  const index lid = kernel().vp_manager.gid_to_lid( source_gid );
  ( *target_to_devices_[ tid ] )[ lid ][ syn_id ]->set_synapse_status( syn_id, cm, d, p );
}

inline void
nest::TargetTableDevices::set_synapse_status_from_device( const thread tid,
  const index ldid,
  const synindex syn_id,
  ConnectorModel& cm,
  const DictionaryDatum& d,
  const port p )
{
  ( *target_from_devices_[ tid ] )[ ldid ][ syn_id ]->set_synapse_status(
    syn_id, cm, d, p );
}

#endif /* TARGET_TABLE_DEVICES_IMPL_H */