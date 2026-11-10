/**
 * @file MarketStressGenerator.js
 * @description Automates stress test scenarios for Phase 11 validation.
 */

import { mockServer } from './MockWebSocketServer';
import { MarketTransitionManager } from '../switching/MarketTransitionManager';

export const MarketStressGenerator = {
    /**
     * SCENARIO: Opening Bell Chaos
     * High volatility, high-frequency ticks (50hz)
     */
    runOpeningBell: () => {
        console.log("[Stress] SCENARIO: Opening Bell Chaos Started.");
        mockServer.start({ 
            tickSpeedMs: 20, 
            volatility: 15,
            symbol: 'NIFTY'
        });
    },

    /**
     * SCENARIO: Rapid Navigation
     * Switches symbols every 2 seconds under heavy load.
     */
    runRapidNavigation: async () => {
        console.log("[Stress] SCENARIO: Rapid Navigation Started.");
        const symbols = ['BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'NIFTY'];
        
        mockServer.start({ tickSpeedMs: 50 });

        for (let i = 0; i < 10; i++) {
            const sym = symbols[i % symbols.length];
            console.log(`[Stress] Forcing switch to ${sym}...`);
            MarketTransitionManager.executeSwitch(sym, '5m');
            await new Promise(r => setTimeout(r, 2000));
        }
        
        console.log("[Stress] Rapid Navigation Scenario Complete.");
    },

    /**
     * SCENARIO: 1000+ MSG/SEC (Extreme Load)
     * Pushes the browser to its limit.
     */
    runExtremeLoad: () => {
        console.log("[Stress] SCENARIO: 1000+ MSG/SEC Extreme Load Started.");
        mockServer.start({ tickSpeedMs: 1, volatility: 2 });
    }
};
