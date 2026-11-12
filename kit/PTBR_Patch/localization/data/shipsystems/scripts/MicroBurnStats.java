package data.shipsystems.scripts;

import java.util.List;

import com.fs.starfarer.api.GameState;
import com.fs.starfarer.api.Global;
import com.fs.starfarer.api.combat.MutableShipStatsAPI;
import com.fs.starfarer.api.combat.ShipAPI;
import com.fs.starfarer.api.combat.ShipAPI.HullSize;
import com.fs.starfarer.api.combat.listeners.AdvanceableListener;
import com.fs.starfarer.api.impl.combat.BaseShipSystemScript;
import com.fs.starfarer.api.plugins.ShipSystemStatsScript;

public class MicroBurnStats extends BaseShipSystemScript {

	public static float POST_ENGINE_BOOST_DUR = 3f;
	public static float POST_ENGINE_BOOST_SPEED = 0f;
	public static float POST_ENGINE_BOOST_TURN_RATE = 0f;
	public static float POST_ENGINE_BOOST_MANEUVERABILITY = 200f;
	
	public static Object STATUS_KEY = new Object();
	public static Object STATUS_KEY2 = new Object();
	
	public static class PBBoostPostSystemUse implements AdvanceableListener {
		public static String BONUS_ID = "PBBoostPostSystemUse_bonus";
		
		public ShipAPI ship;
		public float dur;
		public PBBoostPostSystemUse(ShipAPI ship, float dur) {
			this.ship = ship;
			this.dur = dur;
			
			String id = BONUS_ID;
			MutableShipStatsAPI stats = ship.getMutableStats();
			float effectLevel = Math.min(1f, dur);
			stats.getMaxSpeed().modifyFlat(id, POST_ENGINE_BOOST_SPEED);
			stats.getAcceleration().modifyPercent(id, POST_ENGINE_BOOST_MANEUVERABILITY * effectLevel);
			stats.getDeceleration().modifyPercent(id, POST_ENGINE_BOOST_MANEUVERABILITY * effectLevel);
			stats.getTurnAcceleration().modifyFlat(id, POST_ENGINE_BOOST_SPEED * effectLevel);
			stats.getTurnAcceleration().modifyPercent(id, POST_ENGINE_BOOST_MANEUVERABILITY * effectLevel);
			stats.getMaxTurnRate().modifyFlat(id, POST_ENGINE_BOOST_TURN_RATE);
			stats.getMaxTurnRate().modifyPercent(id, POST_ENGINE_BOOST_MANEUVERABILITY * 0.5f);
		}

		public void resetDur(float dur) {
			this.dur = Math.max(this.dur, dur);
		}
		
		public void advance(float amount) {
			dur -= amount;
			
			if (Global.getCurrentState() == GameState.COMBAT &&
					Global.getCombatEngine() != null && Global.getCombatEngine().getPlayerShip() == ship) {
				Global.getCombatEngine().maintainStatusForPlayerShip(STATUS_KEY,
						Global.getSettings().getSpriteName("ui", "icon_tactical_plasma_burn"),
						"RESUDIAL PLASMA", "IMPROVED MANEUVERABILITY", false);
				if (POST_ENGINE_BOOST_SPEED > 0) {
					Global.getCombatEngine().maintainStatusForPlayerShip(STATUS_KEY2,
							Global.getSettings().getSpriteName("ui", "icon_tactical_plasma_burn"),
							"RESUDIAL PLASMA", "+" + (int)POST_ENGINE_BOOST_SPEED + " TOP SPEED", false);
				}
			}
			
			if (dur <= 0) {
				ship.removeListener(this);
				
				String id = BONUS_ID;
				MutableShipStatsAPI stats = ship.getMutableStats();
				stats.getMaxSpeed().unmodify(id);
				stats.getMaxTurnRate().unmodify(id);
				stats.getTurnAcceleration().unmodify(id);
				stats.getAcceleration().unmodify(id);
				stats.getDeceleration().unmodify(id);
			}
		}
	}	
	
	
	public void addEngineBoostIfNeeded(MutableShipStatsAPI stats) {
		if (stats.getEntity() instanceof ShipAPI) {
			ShipAPI s = (ShipAPI) stats.getEntity();
			List<PBBoostPostSystemUse> listeners = s.getListeners(PBBoostPostSystemUse.class);
			if (listeners.isEmpty()) {
				s.addListener(new PBBoostPostSystemUse(s, POST_ENGINE_BOOST_DUR));
			} else {
				((PBBoostPostSystemUse)listeners.get(0)).resetDur(POST_ENGINE_BOOST_DUR);
			}
		}
	}
	
	public void apply(MutableShipStatsAPI stats, String id, State state, float effectLevel) {
		if (state == ShipSystemStatsScript.State.OUT) {
			addEngineBoostIfNeeded(stats);
			stats.getMaxSpeed().unmodify(id); // to slow down ship to its regular top speed while powering drive down
		} else {
			stats.getMaxSpeed().modifyFlat(id, 600f * effectLevel);
			stats.getAcceleration().modifyFlat(id, 1200f * effectLevel);
		}
	}
	public void unapply(MutableShipStatsAPI stats, String id) {
		stats.getMaxSpeed().unmodify(id);
		stats.getAcceleration().unmodify(id);
	}
	
	public StatusData getStatusData(int index, State state, float effectLevel) {
		if (index == 0) {
			return new StatusData("potência do motor aumentada", false);
		}
		return null;
	}
	
	
	public float getActiveOverride(ShipAPI ship) {
//		if (ship.getHullSize() == HullSize.FRIGATE) {
//			return 1.25f;
//		}
//		if (ship.getHullSize() == HullSize.DESTROYER) {
//			return 0.75f;
//		}
//		if (ship.getHullSize() == HullSize.CRUISER) {
//			return 0.5f;
//		}
		return -1;
	}
	public float getInOverride(ShipAPI ship) {
		return -1;
	}
	public float getOutOverride(ShipAPI ship) {
		return -1;
	}
	
	public float getRegenOverride(ShipAPI ship) {
		return -1;
	}

	public int getUsesOverride(ShipAPI ship) {
		if (ship.getHullSize() == HullSize.FRIGATE) {
			return 2;
		}
		if (ship.getHullSize() == HullSize.DESTROYER) {
			return 2;
		}
		if (ship.getHullSize() == HullSize.CRUISER) {
			return 2;
		}
		return -1;
	}
}


