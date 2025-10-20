import { describe, test, expect, beforeEach, vi } from 'vitest';
import { layoutsService } from '../app/services/layoutsService.js';

// Mock the api module
vi.mock('../app/services/api.js', () => ({
  api: {
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

import { api } from '../app/services/api.js';

describe('layoutsService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('reloadLayout', () => {
    test('should call api.post with correct parameters for reloadLayout', async () => {
      const mockResponse = { data: { layout: { id: 1 } } };
      api.post.mockResolvedValue(mockResponse);

      const result = await layoutsService.reloadLayout(
        'group123',
        'channel456',
        2,
        true,
        '10'
      );

      expect(api.post).toHaveBeenCalledWith('/api/layouts/group123/reload', {
        channel_id: 'channel456',
        columns: 2,
        no_crop: true,
        border_width: '10',
      });
      expect(result).toEqual({ layout: { id: 1 } });
    });

    test('should call api.post with default parameters', async () => {
      const mockResponse = { data: { layout: { id: 1 } } };
      api.post.mockResolvedValue(mockResponse);

      const result = await layoutsService.reloadLayout('group123', 'channel456');

      expect(api.post).toHaveBeenCalledWith('/api/layouts/group123/reload', {
        channel_id: 'channel456',
        border_width: '0',
      });
      expect(result).toEqual({ layout: { id: 1 } });
    });

    test('should call api.post without columns when null', async () => {
      const mockResponse = { data: { layout: { id: 1 } } };
      api.post.mockResolvedValue(mockResponse);

      const result = await layoutsService.reloadLayout(
        'group123',
        'channel456',
        null,
        false,
        '5'
      );

      expect(api.post).toHaveBeenCalledWith('/api/layouts/group123/reload', {
        channel_id: 'channel456',
        border_width: '5',
      });
      expect(result).toEqual({ layout: { id: 1 } });
    });

    test('should throw error when groupedId is missing', async () => {
      await expect(layoutsService.reloadLayout(null, 'channel456')).rejects.toThrow(
        'groupedId is required to reload layout'
      );
    });

    test('should throw error when channelId is missing', async () => {
      await expect(layoutsService.reloadLayout('group123', null)).rejects.toThrow(
        'channelId is required to reload layout'
      );
    });
  });

  describe('updateBorder', () => {
    test('should call api.patch with correct parameters for updateBorder', async () => {
      const mockResponse = { data: { layout: { border_width: '15' } } };
      api.patch.mockResolvedValue(mockResponse);

      const result = await layoutsService.updateBorder('group123', 'channel456', '15');

      expect(api.patch).toHaveBeenCalledWith('/api/layouts/group123/border', {
        channel_id: 'channel456',
        border_width: '15',
      });
      expect(result).toEqual({ layout: { border_width: '15' } });
    });

    test('should throw error when groupedId is missing', async () => {
      await expect(layoutsService.updateBorder(null, 'channel456', '10')).rejects.toThrow(
        'groupedId is required to update border'
      );
    });

    test('should throw error when channelId is missing', async () => {
      await expect(layoutsService.updateBorder('group123', null, '10')).rejects.toThrow(
        'channelId is required to update border'
      );
    });
  });
});