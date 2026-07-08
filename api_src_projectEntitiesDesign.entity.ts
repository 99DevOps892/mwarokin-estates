import { 
  Entity, 
  PrimaryGeneratedColumn, 
  Column, 
  ManyToOne, 
  JoinColumn,
  CreateDateColumn,
  UpdateDateColumn 
} from 'typeorm';
import { Project } from './project.entity';

// Type definitions for better type safety
export type GeometryType = 'box' | 'plane' | 'sphere' | 'cylinder' | 'custom';
export type MaterialType = 'standard' | 'physical' | 'pbr';

export interface GeometryData {
  type: GeometryType;
  vertices: number[];
  dimensions?: [number, number, number];
  rotation?: [number, number, number];
  scale?: [number, number, number];
}

export interface MaterialProperties {
  name: string;
  type: MaterialType;
  color: string;
  textureUrl?: string;
  normalMapUrl?: string;
  roughness: number;
  metallic: number;
  emissive?: string;
  emissiveIntensity?: number;
  transparent?: boolean;
  opacity?: number;
}

export interface DesignMetadata {
  layer: string;
  category: string;
  structural: boolean;
  loadBearing?: boolean;
  tags?: string[];
  version: number;
  lastModifiedBy?: string;
}

@Entity('design_elements')
export class DesignElement {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'varchar', length: 255 })
  name: string;

  @Column({ type: 'varchar', length: 500, nullable: true })
  description: string;

  @Column('jsonb', {
    transformer: {
      to: (value: GeometryData) => value,
      from: (value: string) => this.validateGeometry(JSON.parse(value))
    }
  })
  geometry: GeometryData;

  @Column('jsonb', {
    transformer: {
      to: (value: MaterialProperties) => value,
      from: (value: string) => this.validateMaterial(JSON.parse(value))
    }
  })
  material: MaterialProperties;

  @Column('decimal', { 
    name: 'position_x',
    precision: 12, 
    scale: 6,
    comment: 'X coordinate in 3D space (meters)'
  })
  positionX: number;

  @Column('decimal', { 
    name: 'position_y',
    precision: 12, 
    scale: 6 
  })
  positionY: number;

  @Column('decimal', { 
    name: 'position_z',
    precision: 12, 
    scale: 6 
  })
  positionZ: number;

  @Column('jsonb', {
    transformer: {
      to: (value: DesignMetadata) => value,
      from: (value: string) => this.validateMetadata(JSON.parse(value))
    }
  })
  metadata: DesignMetadata;

  @Column({ 
    type: 'enum', 
    enum: ['draft', 'active', 'archived', 'deleted'],
    default: 'active'
  })
  status: string;

  @Column({ type: 'int', default: 1 })
  version: number;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;

  @Column({ name: 'created_by', type: 'varchar', length: 255, nullable: true })
  createdBy: string;

  @ManyToOne(() => Project, project => project.elements, {
    onDelete: 'CASCADE',
    nullable: false
  })
  @JoinColumn({ name: 'project_id' })
  project: Project;

  @Column({ name: 'project_id' })
  projectId: string;

  // Static validation methods
  private static validateGeometry(geometry: any): GeometryData {
    const required = ['type', 'vertices'];
    required.forEach(field => {
      if (!(field in geometry)) {
        throw new Error(`Missing required geometry field: ${field}`);
      }
    }

    if (!Array.isArray(geometry.vertices)) {
      throw new Error('Geometry vertices must be an array');
    }

    return geometry as GeometryData;
  }

  private static validateMaterial(material: any): MaterialProperties {
    const required = ['name', 'type', 'color', 'roughness', 'metallic'];
    required.forEach(field => {
      if (!(field in material)) {
        throw new Error(`Missing required material field: ${field}`);
      }
    }

    if (material.roughness < 0 || material.roughness > 1) {
      throw new Error('Material roughness must be between 0 and 1');
    }

    if (material.metallic < 0 || material.metallic > 1) {
      throw new Error('Material metallic must be between 0 and 1');
    }

    return material as MaterialProperties;
  }

  private static validateMetadata(metadata: any): DesignMetadata {
    const required = ['layer', 'category', 'structural', 'version'];
    required.forEach(field => {
      if (!(field in metadata)) {
        throw new Error(`Missing required metadata field: ${field}`);
      }
    }

    return {
      tags: [],
      ...metadata
    } as DesignMetadata;
  }

  // Helper methods
  getPosition(): [number, number, number] {
    return [this.positionX, this.positionY, this.positionZ];
  }

  setPosition(x: number, y: number, z: number): void {
    this.positionX = x;
    this.positionY = y;
    this.positionZ = z;
  }

  isStructural(): boolean {
    return this.metadata.structural;
  }

  updateVersion(): void {
    this.version += 1;
    this.metadata.version = this.version;
  }
}
```

## Key Improvements:

1. **Type Safety**: Strongly typed interfaces for JSONB columns
2. **Validation**: JSON transformers with validation logic
3. **Naming Conventions**: Snake_case for database columns
4. **Audit Fields**: Created/updated timestamps and user tracking
5. **Status Management**: Element lifecycle states
6. **Version Control**: Automatic version tracking
7. **Extended Geometry**: Support for more primitive types
8. **Enhanced Materials**: PBR material properties
9. **Helper Methods**: Position management and business logic
10. **Cascade Operations**: Proper relationship configuration
11. **Documentation**: Column comments and clear structure
12. **Error Handling**: Validation with meaningful error messages

## Additional Migration File:

```typescript
// Example migration for the changes
import { MigrationInterface, QueryRunner } from 'typeorm';

export class ModernizeDesignElements1712345678901 implements MigrationInterface {
  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      ALTER TABLE design_elements 
      ADD COLUMN name VARCHAR(255) NOT NULL DEFAULT 'Unnamed Element',
      ADD COLUMN description VARCHAR(500),
      ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'active',
      ADD COLUMN version INTEGER NOT NULL DEFAULT 1,
      ADD COLUMN created_at TIMESTAMP DEFAULT NOW(),
      ADD COLUMN updated_at TIMESTAMP DEFAULT NOW(),
      ADD COLUMN created_by VARCHAR(255),
      RENAME COLUMN positionX TO position_x,
      RENAME COLUMN positionY TO position_y,
      RENAME COLUMN positionZ TO position_z;
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // Down migration logic
  }
}
```

This upgrade provides a more robust, maintainable, and feature-rich design element entity suitable for modern 3D design applications.