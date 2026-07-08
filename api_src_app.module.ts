import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { join } from 'path';
import { validate } from './config/env.validation';
import { AuthModule } from './auth/auth.module';
import { ProjectModule } from './project/project.module';
import { AIModule } from './ai/ai.module';
import { RenderModule } from './render/render.module';
import { WebSocketModule } from './websocket/websocket.module';

@Module({
  imports: [
    // Environment configuration
    ConfigModule.forRoot({
      isGlobal: true,
      validate,
      envFilePath: [`.env.${process.env.NODE_ENV || 'development'}`, '.env'],
    }),

    // Database configuration with environment variables
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (configService: ConfigService) => ({
        type: 'postgres',
        host: configService.getOrThrow('DB_HOST'),
        port: configService.get<number>('DB_PORT', 5432),
        database: configService.getOrThrow('DB_NAME'),
        username: configService.getOrThrow('DB_USERNAME'),
        password: configService.getOrThrow('DB_PASSWORD'),
        entities: [join(__dirname, '**', '*.entity.{ts,js}')],
        synchronize: configService.get<boolean>('DB_SYNCHRONIZE', false),
        logging: configService.get<boolean>('DB_LOGGING', false),
        // Additional modern TypeORM options
        extra: {
          connectionLimit: configService.get<number>('DB_CONNECTION_LIMIT', 10),
        },
        // Enable connection pooling in production
        poolSize: configService.get<number>('DB_POOL_SIZE', 10),
        // SSL configuration for production
        ssl: configService.get<boolean>('DB_SSL', false)
          ? { rejectUnauthorized: false }
          : false,
      }),
    }),

    // Feature modules
    AuthModule,
    ProjectModule,
    AIModule,
    RenderModule,
    WebSocketModule,
  ],
})
export class AppModule {}
```

Additionally, create these supporting files:

**`src/config/env.validation.ts`**
```typescript
import { plainToInstance } from 'class-transformer';
import { IsBoolean, IsNumber, IsString, validateSync } from 'class-validator';

class EnvironmentVariables {
  @IsString()
  DB_HOST: string;

  @IsNumber()
  DB_PORT: number;

  @IsString()
  DB_NAME: string;

  @IsString()
  DB_USERNAME: string;

  @IsString()
  DB_PASSWORD: string;

  @IsBoolean()
  DB_SYNCHRONIZE: boolean;

  @IsBoolean()
  DB_LOGGING: boolean;
}

export function validate(config: Record<string, unknown>) {
  const validatedConfig = plainToInstance(EnvironmentVariables, config, {
    enableImplicitConversion: true,
  });

  const errors = validateSync(validatedConfig, {
    skipMissingProperties: false,
  });

  if (errors.length > 0) {
    throw new Error(errors.toString());
  }
  return validatedConfig;
}
```

**`.env.example`**
```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mwarokin
DB_USERNAME=your_username
DB_PASSWORD=your_password
DB_SYNCHRONIZE=false
DB_LOGGING=true
DB_SSL=false
DB_POOL_SIZE=10
DB_CONNECTION_LIMIT=10

# Application
NODE_ENV=development
```

## Key Improvements:

1. **Environment Configuration**: Uses `@nestjs/config` for robust environment management
2. **Validation**: Adds environment variable validation with class-validator
3. **Async Configuration**: Uses `forRootAsync` for better configuration management
4. **Security**: Removes hardcoded database name and adds proper SSL handling
5. **Production Readiness**: 
   - Disables synchronize by default (use migrations in production)
   - Adds connection pooling
   - SSL support for production databases
6. **Path Handling**: Uses `join` from path module for better cross-platform compatibility
7. **Type Safety**: Full TypeScript type safety with ConfigService
8. **Scalability**: Better database connection management

## Next Steps:

1. Install required dependencies:
```bash
npm install @nestjs/config class-validator class-transformer
```

2. Create separate `.env.development` and `.env.production` files
3. Set up database migrations for production deployments
4. Consider adding health checks and monitoring modules

This modern approach provides better security, maintainability, and production readiness.