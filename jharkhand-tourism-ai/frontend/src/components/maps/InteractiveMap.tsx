import React from 'react';
import { Box, Typography } from '@mui/material';

const InteractiveMap: React.FC = () => {
  return (
    <Box sx={{ height: '400px', bgcolor: 'grey.200', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Typography variant="h6" color="text.secondary">
        Interactive Jharkhand Tourism Map - Coming Soon
      </Typography>
    </Box>
  );
};

export default InteractiveMap;